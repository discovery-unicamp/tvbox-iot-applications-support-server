APP_NAME := totemUpdateCLI
OUTPUT_DIR := bin

.PHONY: all build build-tx2 clean

all: build

build:
	@echo "-> building for current system"
	go build -o $(OUTPUT_DIR)/$(APP_NAME) .

build-linux-amd64:
	@echo "-> building for amd64 linux"
	GOOS=linux GOARCH=amd64 go build -o $(OUTPUT_DIR)/$(APP_NAME) .

clean:
	@echo "-> cleaning build files"
	rm -rf $(OUTPUT_DIR)
