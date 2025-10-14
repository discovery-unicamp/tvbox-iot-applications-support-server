package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"net/http/httputil"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

type config struct {
	URL      string `json:"url"`
	Username string `json:"username"`
	Password string `json:"password"`
}

func main() {
	flag.Bool("local", false, "Upload via USB")
	flag.Parse()

	cfg := checkConfig()

	pioPath := checkPlatformio()

	if isFlagPassed("local") {
		upload2Device(pioPath)
	} else {
		v := buildBin(pioPath)
		upload2Server(cfg, v)
	}
}

func isFlagPassed(name string) bool {
	found := false
	flag.Visit(func(f *flag.Flag) {
		if f.Name == name {
			found = true
		}
	})
	return found
}

func checkPlatformio() string {
	_, err := os.Stat("./platformio.ini")

	if err != nil {
		fmt.Println("🛑 Make sure you are in the same folder as the file platformio.ini")
		os.Exit(1)
	}

	fmt.Println("✅ Found platformio.ini\n")

	pioPath := ""

	_, err = exec.LookPath(".platformio/penv/bin/pio")
	if err != nil {
		_, err = exec.LookPath("pio")
		if err != nil {
			fmt.Println("🛑 Could not find platformio executable")
			os.Exit(1)
		} else {
			pioPath = "pio"
		}
	} else {
		pioPath = ".platformio/penv/bin/pio"
	}

	return pioPath
}

func buildBin(pioPath string) int64 {
	fmt.Println("⏳ Building the binary...")

	tz, _ := time.LoadLocation("America/Sao_Paulo")
	version := time.Now().In(tz).Unix()

	cmd := exec.Command(pioPath, "run", "-e", "nodemcuv2")
	cmd.Env = append(os.Environ(), "PLATFORMIO_BUILD_FLAGS='-DVERSION="+strconv.FormatInt(version, 10)+"'")

	out, _ := cmd.CombinedOutput()

	if !strings.Contains(string(out), "SUCCESS") {
		fmt.Println("🛑 Build was not successful\n")
		fmt.Println(string(out))
		os.Exit(1)
	}

	fmt.Println("✅ Successfully built binary!\n")
	return version
}

func upload2Device(pioPath string) {
	fmt.Println("⏳ Uploading to the device...")

	tz, _ := time.LoadLocation("America/Sao_Paulo")
	version := time.Now().In(tz).Unix()

	cmd := exec.Command(pioPath, "run", "-t", "upload", "-e", "nodemcuv2")
	cmd.Env = append(os.Environ(), "PLATFORMIO_BUILD_FLAGS='-DVERSION="+strconv.FormatInt(version, 10)+"'")

	out, _ := cmd.CombinedOutput()

	if !strings.Contains(string(out), "SUCCESS") {
		fmt.Println("🛑 Upload to device was not successful\n")
		fmt.Println(string(out))
		os.Exit(1)
	}

	fmt.Println("✅ Successfully uploaded firmware!\n")
}

func upload2Server(cfg config, version int64) {
	fmt.Println("⏳ Uploading bin to update server...")

	data, err := os.ReadFile(".pio/build/nodemcuv2/firmware.bin")
	if err != nil {
		fmt.Println("🛑 Could not find binary file")
		os.Exit(1)
	}

	req, err := http.NewRequest("POST", cfg.URL+"/totem/upload?version="+strconv.FormatInt(version, 10), bytes.NewReader(data))
	if err != nil {
		panic(err)
	}
	req.Header.Set("Content-Type", "application/octet-stream")
	req.SetBasicAuth(cfg.Username, cfg.Password)

	dump, err := httputil.DumpRequest(req, false)
	if err != nil {
		panic(err)
	}
	fmt.Println(string(dump))

	client := &http.Client{}
	res, err := client.Do(req)

	if err != nil {
		fmt.Println("🛑 " + err.Error())
		os.Exit(1)
	}

	dump, err = httputil.DumpResponse(res, true)
	if err != nil {
		panic(err)
	}
	fmt.Println(string(dump))

	switch res.StatusCode {
	case 200:
		fmt.Println("✅ Successfully uploaded binary!\n")
		fmt.Println("🗓️ Current version: " + strconv.FormatInt(version, 10))

		return
	case 400:
		fmt.Println("🛑 Bad Request")
		os.Exit(1)
	case 401:
		fmt.Println("🛑 The credentials were not valid, update the cache file")
		os.Exit(1)
	case 409:
		fmt.Println("🛑 This version already exists")
		os.Exit(1)
	default:
		fmt.Println("🛑 Unexpected HTTP status code: " + strconv.Itoa(res.StatusCode))
		os.Exit(1)
	}
}

func checkConfig() config {
	details := config{}

	file, err := os.Open("./totemUpdateCache.json")
	if err != nil {
		reader := bufio.NewReader(os.Stdin)

		fmt.Println("⬇️ Fill in the endpoint information:")

		fmt.Print("\tServer endpoint: ")
		url, _ := reader.ReadString('\n')
		details.URL = strings.TrimSpace(url)

		fmt.Print("\tUsername: ")
		username, _ := reader.ReadString('\n')
		details.Username = strings.TrimSpace(username)

		fmt.Print("\tPassword: ")
		password, _ := reader.ReadString('\n')
		details.Password = strings.TrimSpace(password)

		file, _ := os.Create("./totemUpdateCache.json")
		defer file.Close()

		fmt.Println("✅ Info stored in cache")

		encoder := json.NewEncoder(file)
		encoder.SetIndent("", "  ")
		encoder.Encode(details)
	} else {
		defer file.Close()

		fmt.Println("✅ Read info cache")

		err = json.NewDecoder(file).Decode(&details)
		if err != nil {
			panic(err)
		}
	}

	return details
}
