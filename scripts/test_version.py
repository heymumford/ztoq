import subprocess
import sys
import os

def test_version_command():
    """Test that the --version flag works correctly."""
    print("Testing 'ztoq --version' command...")
    
    try:
        # Use subprocess to run the command
        result = subprocess.run(
            ["ztoq", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        
        # Check if the output contains the version
        if "ZTOQ version:" in result.stdout:
            print("✅ Success! Version command works correctly.")
            print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ Error: Version command did not return expected output.")
            print(f"Output: {result.stdout.strip()}")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {e}")
        print(f"Stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    # Run the test
    success = test_version_command()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)