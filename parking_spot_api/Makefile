APP_NAME := parkingLotServer
OUTPUT_DIR := bin

.PHONY: all build build-tx2 clean

all: build

build:
	@echo "-> building for current system"
	go build -o $(OUTPUT_DIR)/$(APP_NAME) .

build-tx2:
	@echo "-> building for armv7 linux (tx2)"
	GOOS=linux GOARCH=arm GOARM=7 go build -o $(OUTPUT_DIR)/$(APP_NAME)-tx2 .

clean:
	@echo "-> cleaning build files"
	rm -rf $(OUTPUT_DIR)