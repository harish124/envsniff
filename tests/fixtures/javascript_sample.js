// Sample JavaScript file with process.env patterns for testing envsniff

// Pattern 1: process.env.VAR (identifier access)
const apiKey = process.env.API_KEY;

// Pattern 2: process.env["VAR"] (subscript access)
const dbUrl = process.env["DATABASE_URL"];

// Pattern 3: with default via || operator
const port = process.env.PORT || "3000";

// Pattern 4: in object destructuring context
const nodeEnv = process.env.NODE_ENV;

// Pattern 5: in function argument
fetch(process.env.API_BASE_URL);

// Pattern 6: subscript with default
const secretKey = process.env["SECRET_KEY"] || "dev-secret";

// Pattern 7: deeply nested
function setup() {
    if (process.env.DEBUG === "true") {
        console.log(process.env.LOG_LEVEL);
    }
}

// Pattern 8: template literal
const dsn = `postgresql://${process.env.DB_USER}:${process.env.DB_PASSWORD}@localhost`;

// Edge case: computed property - should not be extracted
const envKey = "DYNAMIC_VAR";
const dynamicVal = process.env[envKey];
