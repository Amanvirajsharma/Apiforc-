from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import uuid
import time

app = FastAPI(
    title="C++ Code Runner API",
    description="Simple API to run C++ code - Just send JSON!",
    version="2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp directory
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.on_event("startup")
async def startup():
    print("✅ C++ Runner API Started - Version 2.0")

@app.get("/")
async def root():
    return {
        "message": "C++ Code Runner API",
        "version": "2.0",
        "usage": {
            "endpoint": "POST /execute",
            "example": {
                "code": "#include <iostream>\nint main() { std::cout << \"Hello!\"; return 0; }",
                "input": "5 10"
            }
        },
        "docs": "/docs"
    }  # ← COMMA REMOVED!

@app.get("/health")
async def health():
    return {"status": "ok", "compiler": "g++"}

@app.post("/execute")
async def execute_code(request: dict):
    """
    Execute C++ code
    
    Request body example:
    {
        "code": "your C++ code here",
        "input": "program input (optional)"
    }
    """
    
    # Get data
    code = request.get("code", "")
    user_input = request.get("input", "")
    
    if not code:
        return {"success": False, "error": "No code provided"}
    
    # Generate unique filenames
    unique_id = str(uuid.uuid4())[:8]
    cpp_file = os.path.join(TEMP_DIR, f"code_{unique_id}.cpp")
    exe_file = os.path.join(TEMP_DIR, f"code_{unique_id}")
    input_file = os.path.join(TEMP_DIR, f"input_{unique_id}.txt")
    
    try:
        # Write code to file
        with open(cpp_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Write input to file if provided
        if user_input:
            with open(input_file, 'w', encoding='utf-8') as f:
                f.write(user_input)
        
        # Compile
        compile_start = time.time()
        compile_cmd = f"g++ {cpp_file} -o {exe_file} -O2 -std=c++17"
        
        compile_result = subprocess.run(
            compile_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        compile_time = time.time() - compile_start
        
        if compile_result.returncode != 0:
            return {
                "success": False,
                "error": compile_result.stderr,
                "stage": "compilation",
                "compile_time": compile_time
            }
        
        # Execute
        exec_start = time.time()
        
        if user_input:
            with open(input_file, 'r') as inp:
                exec_result = subprocess.run(
                    [exe_file],
                    stdin=inp,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
        else:
            exec_result = subprocess.run(
                [exe_file],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        exec_time = time.time() - exec_start
        
        if exec_result.returncode != 0 and exec_result.stderr:
            return {
                "success": False,
                "error": exec_result.stderr,
                "stage": "execution",
                "compile_time": compile_time,
                "exec_time": exec_time
            }
        
        return {
            "success": True,
            "output": exec_result.stdout,
            "compile_time": compile_time,
            "exec_time": exec_time
        }
    
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Time limit exceeded"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        # Cleanup
        for file in [cpp_file, exe_file, input_file]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

@app.get("/examples")
async def examples():
    return {
        "hello_world": {
            "code": "#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << \"Hello World!\" << endl;\n    return 0;\n}",
            "input": ""
        },
        "sum": {
            "code": "#include <iostream>\nusing namespace std;\n\nint main() {\n    int a, b;\n    cin >> a >> b;\n    cout << \"Sum: \" << (a + b) << endl;\n    return 0;\n}",
            "input": "10 20"
        },
        "fibonacci": {
            "code": "#include <iostream>\nusing namespace std;\n\nint main() {\n    int n;\n    cin >> n;\n    int a = 0, b = 1;\n    for(int i = 0; i < n; i++) {\n        cout << a << \" \";\n        int temp = a + b;\n        a = b;\n        b = temp;\n    }\n    cout << endl;\n    return 0;\n}",
            "input": "10"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)