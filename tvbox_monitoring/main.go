package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/influxdata/influxdb-client-go/v2"
	"github.com/influxdata/influxdb-client-go/v2/api"
	"github.com/influxdata/influxdb-client-go/v2/api/write"
	"github.com/joho/godotenv"
	"github.com/redis/go-redis/v9"
	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/mem"
)

type TVBoxStatus struct {
	CpuUsage       float64   `json:"cpuUsage"`
	CpuTemperature float64   `json:"cpuTemperature"`
	MemoryUsage    float64   `json:"memoryUsage"`
	Time           time.Time `json:"time"`
}

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Fatalf("Error loading .env file: %s", err)
	}

	ctx := context.Background()

	token := os.Getenv("INFLUX_TOKEN")
	url := os.Getenv("INFLUX_ADDR")

	influxClient := influxdb2.NewClient(url, token)
	writeAPI := influxClient.WriteAPIBlocking(os.Getenv("INFLUX_ORG"), os.Getenv("INFLUX_BUCKET"))

	redisClient := redis.NewClient(&redis.Options{
		Addr:     "localhost:6379",
		Password: "",
		DB:       0,
	})

	defer influxClient.Close()
	defer redisClient.Close()

	fmt.Println("Initializing routines...")

	var wg sync.WaitGroup
	wg.Add(2)
	go readWorker(ctx, redisClient)
	go uploadWorker(ctx, redisClient, writeAPI)
	wg.Wait()
}

func readStatus() (TVBoxStatus, error) {
	percent, err := cpu.Percent(time.Second, false)
	if err != nil {
		return TVBoxStatus{}, err
	}

	tempRaw, err := os.ReadFile("/sys/class/hwmon/hwmon0/temp1_input")
	if err != nil {
		return TVBoxStatus{}, err
	}
	temp, err := strconv.ParseFloat(strings.TrimSpace(string(tempRaw)), 64)
	if err != nil {
		return TVBoxStatus{}, err
	}

	vm, err := mem.VirtualMemory()
	if err != nil {
		return TVBoxStatus{}, err
	}

	return TVBoxStatus{
		CpuUsage:       percent[0],
		CpuTemperature: temp / 1000,
		MemoryUsage:    vm.UsedPercent,
		Time:           time.Now(),
	}, nil
}

func readWorker(ctx context.Context, redis *redis.Client) {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		status, err := readStatus()
		if err != nil {
			log.Println("Error reading status:", err)
			continue
		}

		statusJson, _ := json.Marshal(status)
		fmt.Println("Reading status:", time.Now().Format("15:04:05"), string(statusJson))
		err = redis.LPush(ctx, "tvbox_status", statusJson).Err()
		if err != nil {
			log.Println("Error pushing status to redis:", err)
		}
	}
}

func uploadWorker(ctx context.Context, redis *redis.Client, writeAPI api.WriteAPIBlocking) {
	ticker := time.NewTicker(15 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		var points []*write.Point

		n := redis.LLen(ctx, "tvbox_status").Val()
		for i := int64(0); i < n; i++ {

			var status TVBoxStatus
			raw := redis.LPop(ctx, "tvbox_status").Val()

			if err := json.Unmarshal([]byte(raw), &status); err != nil {
				log.Println("Error unmarshalling redis status:", err)
				continue
			}

			deviceName := os.Getenv("DEVICE_NAME")
			if deviceName == "" {
				deviceName = "tvbox-unknown"
			}

			points = append(points, influxdb2.NewPoint(
				"status",
				map[string]string{"device": deviceName},
				map[string]interface{}{
					"cpu_usage":       status.CpuUsage,
					"cpu_temperature": status.CpuTemperature,
					"memory_usage":    status.MemoryUsage,
				},
				status.Time,
			))
		}

		fmt.Println("Uploading status")
		err := writeAPI.WritePoint(ctx, points...)
		if err != nil {
			log.Println("Error writing points to influx:", err)
		}
	}
}
