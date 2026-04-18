// Sample Go file with os.Getenv / os.LookupEnv patterns for testing envsniff

package main

import (
	"fmt"
	"os"
)

func main() {
	// Pattern 1: os.Getenv
	apiKey := os.Getenv("API_KEY")
	fmt.Println(apiKey)

	// Pattern 2: os.LookupEnv
	dbURL, ok := os.LookupEnv("DATABASE_URL")
	if !ok {
		panic("DATABASE_URL not set")
	}
	fmt.Println(dbURL)

	// Pattern 3: os.Getenv in expression
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	// Pattern 4: os.Getenv in function call
	fmt.Println(os.Getenv("LOG_LEVEL"))

	// Pattern 5: os.LookupEnv with multiline handling
	secretToken, found := os.LookupEnv("SECRET_TOKEN")
	if !found {
		secretToken = "default-token"
	}
	_ = secretToken
	_ = port
}
