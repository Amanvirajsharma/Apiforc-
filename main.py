from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os
import uuid
import shutil
from typing import Optional
import time

app = FastAPI(title="Universal C++ Code Runner API")

# CORS for Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directory
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Models
class CodeRequest(BaseModel):
    code: str
    input: Optional[str] = ""
    timeout: Optional[int] = 10
    compiler_flags: Optional[str] = "-O2 -std=c++17"

class CodeResponse(BaseModel):
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    compilation_time: Optional[float] = None
    execution_time: Optional[float] = None
    memory_used: Optional[str] = None

# Cleanup old files
def cleanup_old_files():
    try:
        for filename in os.listdir(TEMP_DIR):
            filepath = os.path.join(TEMP_DIR, filename)
            if os.path.isfile(filepath):
                if time.time() - os.path.getmtime(filepath) > 3600:  # 1 hour
                    os.remove(filepath)
    except Exception as e:
        print(f"Cleanup error: {e}")

@app.on_event("startup")
async def startup():
    cleanup_old_files()
    print("✅ C++ Runner API Started")

@app.get("/")
async def root():
    return {
        "message": "Universal C++ Code Runner",
        "version": "1.0",
        "endpoints": {
            "/run": "POST - Execute any C++ code",
            "/health": "GET - Health check",
            "/examples": "GET - Get example codes"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "compiler": "g++",
        "temp_dir": os.path.exists(TEMP_DIR)
    }

@app.post("/run", response_model=CodeResponse)
async def run_code(request: CodeRequest):
    """
    Execute any C++ code
    """
    unique_id = str(uuid.uuid4())[:8]
    cpp_file = os.path.join(TEMP_DIR, f"code_{unique_id}.cpp")
    exe_file = os.path.join(TEMP_DIR, f"code_{unique_id}")
    input_file = os.path.join(TEMP_DIR, f"input_{unique_id}.txt")
    
    try:
        # Write C++ code to file
        with open(cpp_file, 'w') as f:
            f.write(request.code)
        
        # Write input if provided
        if request.input:
            with open(input_file, 'w') as f:
                f.write(request.input)
        
        # Compile
        compile_start = time.time()
        compile_cmd = f"g++ {cpp_file} -o {exe_file} {request.compiler_flags}"
        
        compile_result = subprocess.run(
            compile_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        compilation_time = time.time() - compile_start
        
        if compile_result.returncode != 0:
            return CodeResponse(
                success=False,
                error=f"Compilation Error:\n{compile_result.stderr}",
                compilation_time=compilation_time
            )
        
        # Execute
        exec_start = time.time()
        
        if request.input:
            with open(input_file, 'r') as input_f:
                exec_result = subprocess.run(
                    [exe_file],
                    stdin=input_f,
                    capture_output=True,
                    text=True,
                    timeout=request.timeout
                )
        else:
            exec_result = subprocess.run(
                [exe_file],
                capture_output=True,
                text=True,
                timeout=request.timeout
            )
        
        execution_time = time.time() - exec_start
        
        if exec_result.returncode != 0:
            return CodeResponse(
                success=False,
                error=f"Runtime Error:\n{exec_result.stderr}",
                compilation_time=compilation_time,
                execution_time=execution_time
            )
        
        return CodeResponse(
            success=True,
            output=exec_result.stdout,
            compilation_time=compilation_time,
            execution_time=execution_time
        )
    
    except subprocess.TimeoutExpired:
        return CodeResponse(
            success=False,
            error="Time Limit Exceeded"
        )
    except Exception as e:
        return CodeResponse(
            success=False,
            error=f"Server Error: {str(e)}"
        )
    finally:
        # Cleanup files
        for file in [cpp_file, exe_file, input_file]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

@app.get("/examples")
async def get_examples():
    return {
        "hello_world": {
            "code": """#include <iostream>
using namespace std;

int main() {
    cout << "Hello, World!" << endl;
    return 0;
}""",
            "input": ""
        },
        "sum_two_numbers": {
            "code": """#include <iostream>
using namespace std;

int main() {
    int a, b;
    cin >> a >> b;
    cout << "Sum: " << (a + b) << endl;
    return 0;
}""",
            "input": "5 10"
        },
        "fibonacci": {
            "code": """#include <iostream>
using namespace std;

int main() {
    int n;
    cin >> n;
    long long a = 0, b = 1;
    
    for(int i = 0; i < n; i++) {
        cout << a << " ";
        long long temp = a + b;
        a = b;
        b = temp;
    }
    return 0;
}""",
            "input": "10"
        },
        "prime_check": {
            "code": """#include <iostream>
#include <cmath>
using namespace std;

bool isPrime(int n) {
    if(n <= 1) return false;
    if(n <= 3) return true;
    if(n % 2 == 0 || n % 3 == 0) return false;
    
    for(int i = 5; i * i <= n; i += 6) {
        if(n % i == 0 || n % (i + 2) == 0)
            return false;
    }
    return true;
}

int main() {
    int num;
    cin >> num;
    
    if(isPrime(num))
        cout << num << " is Prime" << endl;
    else
        cout << num << " is Not Prime" << endl;
    
    return 0;
}""",
            "input": "17"
        },
        "array_operations": {
            "code": """#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> arr(n);
    
    for(int i = 0; i < n; i++)
        cin >> arr[i];
    
    sort(arr.begin(), arr.end());
    
    cout << "Sorted: ";
    for(int x : arr)
        cout << x << " ";
    cout << endl;
    
    cout << "Min: " << arr[0] << endl;
    cout << "Max: " << arr[n-1] << endl;
    
    return 0;
}""",
            "input": "5\n3 1 4 1 5"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)