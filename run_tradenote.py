#!/usr/bin/env python
import subprocess
import os
import sys
import time
import signal
import webbrowser
import threading
import platform

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Global variables to track processes
frontend_process = None
backend_process = None
processes_started = False

def print_banner():
    """Print a nice banner when starting the application"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}===================================={Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}         TRADENOTE LAUNCHER         {Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}===================================={Colors.ENDC}\n")
    print(f"{Colors.YELLOW}Starting backend and frontend servers...{Colors.ENDC}\n")

def cleanup(signum=None, frame=None):
    """Clean up processes when exiting"""
    global frontend_process, backend_process, processes_started
    
    if not processes_started:
        return
        
    print(f"\n{Colors.YELLOW}Shutting down servers...{Colors.ENDC}")
    
    # Terminate processes based on the platform
    if platform.system() == 'Windows':
        if frontend_process:
            # On Windows, we need to use taskkill to properly terminate the process tree
            subprocess.run(f"taskkill /F /T /PID {frontend_process.pid}", shell=True)
        if backend_process:
            subprocess.run(f"taskkill /F /T /PID {backend_process.pid}", shell=True)
    else:
        # On Unix systems, we can use process groups
        if frontend_process:
            try:
                os.killpg(os.getpgid(frontend_process.pid), signal.SIGTERM)
            except:
                pass
        if backend_process:
            try:
                os.killpg(os.getpgid(backend_process.pid), signal.SIGTERM)
            except:
                pass
    
    print(f"{Colors.GREEN}All servers shut down.{Colors.ENDC}")
    sys.exit(0)

def start_backend():
    """Start the backend server"""
    global backend_process
    
    backend_dir = os.path.join(os.getcwd(), "backend")
    print(f"{Colors.BLUE}Starting backend server from {backend_dir}{Colors.ENDC}")
    
    # Use shell=True on Windows, and create_new_process_group to enable sending signals
    if platform.system() == 'Windows':
        backend_process = subprocess.Popen(
            ["python", "run.py"],
            cwd=backend_dir,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        backend_process = subprocess.Popen(
            ["python", "run.py"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid
        )
    
    print(f"{Colors.GREEN}Backend server started (PID: {backend_process.pid}){Colors.ENDC}")
    return backend_process

def start_frontend():
    """Start the frontend server"""
    global frontend_process
    
    # Wait a moment for backend to initialize
    time.sleep(2)
    
    print(f"{Colors.BLUE}Starting frontend development server{Colors.ENDC}")
    
    # Use shell=True on Windows, and create_new_process_group to enable sending signals
    if platform.system() == 'Windows':
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=os.getcwd(),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid
        )
    
    print(f"{Colors.GREEN}Frontend server started (PID: {frontend_process.pid}){Colors.ENDC}")
    return frontend_process

def monitor_process_output(process, prefix):
    """Monitor and print process output with a prefix"""
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        print(f"{prefix} {line.rstrip()}")

def open_browser(url, delay=5):
    """Open the browser after a delay to give servers time to start"""
    time.sleep(delay)
    print(f"{Colors.GREEN}Opening TradeNote in your browser...{Colors.ENDC}")
    webbrowser.open(url)

def main():
    global processes_started
    
    print_banner()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Start backend
        backend = start_backend()
        
        # Start frontend
        frontend = start_frontend()
        
        processes_started = True
        
        # Start output monitor threads
        backend_thread = threading.Thread(
            target=monitor_process_output, 
            args=(backend, f"{Colors.BLUE}[Backend]{Colors.ENDC}"),
            daemon=True
        )
        frontend_thread = threading.Thread(
            target=monitor_process_output, 
            args=(frontend, f"{Colors.GREEN}[Frontend]{Colors.ENDC}"),
            daemon=True
        )
        
        backend_thread.start()
        frontend_thread.start()
        
        # Open browser after delay
        browser_thread = threading.Thread(
            target=open_browser,
            args=("http://localhost:5173",),
            daemon=True
        )
        browser_thread.start()
        
        print(f"\n{Colors.BOLD}{Colors.GREEN}TradeNote is starting!{Colors.ENDC}")
        print(f"{Colors.YELLOW}Press Ctrl+C to shut down all servers{Colors.ENDC}\n")
        
        # Wait for processes to complete
        backend.wait()
        frontend.wait()
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Received keyboard interrupt. Shutting down...{Colors.ENDC}")
    finally:
        cleanup()

if __name__ == "__main__":
    main() 