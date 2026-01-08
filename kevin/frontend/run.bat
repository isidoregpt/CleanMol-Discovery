@echo off
echo Starting Kevin Frontend...

if not exist node_modules (
    echo Installing dependencies...
    npm install
)

echo Starting dev server on http://localhost:3000
npm run dev
