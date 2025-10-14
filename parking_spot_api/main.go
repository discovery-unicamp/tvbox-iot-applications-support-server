package main

import (
	"bytes"
	"fmt"
	"io"
	"log"
	"math/bits"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/joho/godotenv"
)

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Fatalf("Error loading .env file: %s", err)
	}

	r := chi.NewRouter()

	r.Use(middleware.Recoverer)
	r.Use(middleware.Logger)

	r.Get("/", redirect)
	r.Get("/last_value", lastValue)
	r.Get("/last_timestamp", lastTimestamp)
	r.Get("/last_spots", lastSpots)

	auth := middleware.BasicAuth("Toggle Access", map[string]string{
		os.Getenv("AUTH_USER"): os.Getenv("AUTH_PASS"),
	})

	r.With(auth).Get("/turnOff", turnOff)
	r.With(auth).Get("/turnOn", turnOn)

	http.ListenAndServe(":8001", r)
}

func checkHeartbeat(h *http.Header) error {
	device := h.Get("Device-Name")
	freeHeapRaw := h.Get("Device-FreeHeap")

	if device == "" || freeHeapRaw == "" {
		return nil
	}

	freeHeap, err := strconv.Atoi(freeHeapRaw)
	if err != nil {
		return err
	}

	url := os.Getenv("INFLUX_ADDR") +
		"/api/v2/write?precision=ns" +
		"&org=" + os.Getenv("INFLUX_ORG") +
		"&bucket=" + os.Getenv("INFLUX_HEARTBEAT_BUCKET")

	loc, _ := time.LoadLocation("America/Sao_Paulo")
	ts := time.Now().In(loc).UnixNano()

	line := fmt.Sprintf("status,device=%s free_heap=%di %d", device, freeHeap, ts)

	req, err := http.NewRequest("POST", url, bytes.NewBuffer([]byte(line)))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "text/plain; charset=utf-8")
	req.Header.Set("Authorization", "Token "+os.Getenv("INFLUX_HEARTBEAT_TOKEN"))

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}

func readInflux() (string, error) {
	url := os.Getenv("INFLUX_ADDR") + "/api/v2/query?org=" + os.Getenv("INFLUX_ORG")

	var query = []byte(`
		from(bucket: "` + os.Getenv("INFLUX_SPOT_BUCKET") + `")
		   |> range(start: -1d)
		   |> keep(columns: ["_value", "_time"])
		   |> last()
	`)

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(query))

	if err != nil {
		return "", err
	}

	req.Header.Set("Accept", "application/csv")
	req.Header.Set("Content-Type", "application/vnd.flux")
	req.Header.Set("Authorization", "Token "+os.Getenv("INFLUX_SPOT_TOKEN"))

	client := &http.Client{}
	resp, err := client.Do(req)

	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	return string(body), nil
}

func redirect(w http.ResponseWriter, req *http.Request) {
	proto := req.Header.Get("X-Forwarded-Proto")
	host := req.Header.Get("X-Forwarded-Host")
	url := fmt.Sprintf("%s://%s/last_value", proto, host)

	http.Redirect(w, req, url, http.StatusFound)
}

func lastValue(w http.ResponseWriter, r *http.Request) {
	err := checkHeartbeat(&r.Header)
	if err != nil {
		http.Error(w, "Error reading heartbeat: "+err.Error(), http.StatusInternalServerError)
	}

	data, err := os.ReadFile("status.txt")
	if err != nil && !os.IsNotExist(err) {
		http.Error(w, "Error reading status file", http.StatusInternalServerError)
	}

	if string(data) == "0" {
		w.Write([]byte("-1"))
		return
	}

	res, err := readInflux()
	if err != nil {
		http.Error(w, "Error accessing database", http.StatusInternalServerError)
		return
	}

	fmt.Println(res)

	csv := strings.Split(res, ",")
	val := strings.TrimSpace(csv[len(csv)-1])

	encoded, err := strconv.Atoi(val)

	if err != nil {
		fmt.Println(err)
		http.Error(w, "Error parsing database response", http.StatusInternalServerError)
		return
	}

	w.Write([]byte(strconv.Itoa(16 - bits.OnesCount(uint(encoded)))))
}

func lastTimestamp(w http.ResponseWriter, r *http.Request) {
	res, err := readInflux()
	if err != nil {
		http.Error(w, "Error accessing database", http.StatusInternalServerError)
		return
	}

	csv := strings.Split(res, ",")
	w.Write([]byte(strings.TrimSpace(csv[len(csv)-2])))
}

func lastSpots(w http.ResponseWriter, r *http.Request) {
	res, err := readInflux()
	if err != nil {
		http.Error(w, "Error accessing database", http.StatusInternalServerError)
		return
	}

	csv := strings.Split(res, ",")
	val := strings.TrimSpace(csv[len(csv)-1])

	w.Write([]byte(val))
}

func turnOff(w http.ResponseWriter, r *http.Request) {
	err := os.WriteFile("status.txt", []byte("0"), 0644)
	if err != nil {
		http.Error(w, "Error updating status", http.StatusInternalServerError)
	}
	w.Write([]byte("Ok"))
}

func turnOn(w http.ResponseWriter, r *http.Request) {
	err := os.WriteFile("status.txt", []byte("1"), 0644)
	if err != nil {
		http.Error(w, "Error updating status", http.StatusInternalServerError)
	}
	w.Write([]byte("Ok"))
}
