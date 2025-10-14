package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

func main() {
	r := chi.NewRouter()

	r.Use(middleware.Recoverer)
	r.Use(middleware.Logger)
	//r.Use(middleware.BasicAuth("Full Access", map[string]string{"user": "pass"}))
	//TODO: Set credentials

	r.Get("/", listVersions)
	r.Get("/update", update)
	r.Post("/upload", upload)

	http.ListenAndServe(":8002", r)
}

func listVersions(w http.ResponseWriter, r *http.Request) {
	list := ""

	err := os.MkdirAll("./firmwares", os.ModePerm)
	versions, err := os.ReadDir("./firmwares")
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		panic("Couldn't read ./firmwares")
		return
	}
	for _, file := range versions {
		if !file.IsDir() {
			list += file.Name() + "\n"
		}
	}

	w.Write([]byte(list))
}

func update(w http.ResponseWriter, r *http.Request) {
	param := r.URL.Query().Get("currentVersion")
	currentVersion, err := strconv.ParseInt(param, 10, 64)

	if currentVersion == 0 || err != nil {
		http.Error(w, "Invalid version", http.StatusBadRequest)
		return
	}

	var latest int64 = 0
	err = os.MkdirAll("./firmwares", os.ModePerm)
	versions, err := os.ReadDir("./firmwares")
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		panic("Couldn't read ./firmwares")
		return
	}
	for _, file := range versions {
		fileName := file.Name()[:strings.IndexByte(file.Name(), '.')]
		version, _ := strconv.ParseInt(fileName, 10, 64)
		fmt.Println(version, latest)
		if !file.IsDir() && version > latest {
			latest = version
		}
	}

	if latest <= currentVersion {
		w.WriteHeader(http.StatusNotModified)
		return
	}

	w.Header().Set("Content-Type", "application/octet-stream")
	w.Header().Set("Content-Disposition", "attachment; filename=\""+strconv.FormatInt(latest, 10)+".bin\"")
	http.ServeFile(w, r, "./firmwares/"+strconv.FormatInt(latest, 10)+".bin")
	w.WriteHeader(http.StatusOK)
}

func upload(w http.ResponseWriter, r *http.Request) {
	param := r.URL.Query().Get("version")
	currentVersion, err := strconv.ParseInt(param, 10, 64)
	if currentVersion == 0 || err != nil {
		http.Error(w, "Invalid version: "+err.Error(), http.StatusBadRequest)
		return
	}

	versions, err := os.ReadDir("./firmwares")
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		panic("Couldn't read ./firmwares")
		return
	}
	for _, file := range versions {
		if !file.IsDir() && file.Name() == param {
			w.WriteHeader(http.StatusConflict)
			return
		}
	}

	if r.Header.Get("Content-Type") != "application/octet-stream" {
		http.Error(w, "Expected content-type application/octet-stream", http.StatusBadRequest)
		return
	}

	dst, err := os.Create("./firmwares/" + param + ".bin")
	if err != nil {
		http.Error(w, "Failed to create file", http.StatusInternalServerError)
		return
	}
	defer dst.Close()

	_, err = io.Copy(dst, r.Body)
	if err != nil {
		http.Error(w, "Failed to save file", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}
