#!/usr/bin/env python3
"""
Simple Hello World program for testing GitHub-to-EXE
Safe, clean code with no external dependencies or risky operations.
"""
import sys

def main():
    print("🎉 Hello from GitHub-to-EXE!")
    print("This executable was built successfully!")

    try:
        # Check if stdin is available (for PyInstaller compatibility)
        if hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
            name = input("What's your name? ")
            print(f"Nice to meet you, {name}!")
        else:
            print("Running in non-interactive mode - that's okay!")
            print("Your executable is working perfectly!")
    except (EOFError, OSError):
        print("Input not available - that's okay!")
        print("Your executable is working perfectly!")

    print("\nBuild completed successfully! ✅")

    # Wait a bit so user can see the output
    try:
        if hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
            input("Press Enter to exit...")
        else:
            import time
            time.sleep(3)
    except:
        import time
        time.sleep(3)

if __name__ == "__main__":
    main()