#!/usr/bin/env python3
"""
Screen sharing diagnostic script.

This script helps diagnose why screen sharing might not be working in the main application.
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox

def check_permissions():
    """Check system permissions for screen capture."""
    print("🔒 Checking System Permissions...")
    
    try:
        import mss
        with mss.mss() as sct:
            # Try to capture screen
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            
            if screenshot and screenshot.width > 0 and screenshot.height > 0:
                print(f"✅ Screen capture permission OK: {screenshot.width}x{screenshot.height}")
                return True
            else:
                print("❌ Screen capture failed - no data returned")
                return False
                
    except Exception as e:
        print(f"❌ Screen capture permission error: {e}")
        return False

def check_dependencies():
    """Check all required dependencies."""
    print("📦 Checking Dependencies...")
    
    missing = []
    
    # Check mss
    try:
        import mss
        print("✅ mss library available")
    except ImportError:
        print("❌ mss library missing")
        missing.append("mss")
    
    # Check PIL
    try:
        from PIL import Image
        print("✅ PIL library available")
    except ImportError:
        print("❌ PIL library missing")
        missing.append("Pillow")
    
    # Check PySide6
    try:
        from PySide6.QtWidgets import QApplication
        print("✅ PySide6 available")
    except ImportError:
        print("❌ PySide6 missing")
        missing.append("PySide6")
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    return True

def check_app_integration():
    """Check if screen sharing is properly integrated in the app."""
    print("🔗 Checking App Integration...")
    
    try:
        # Check if app.py has the screen share handlers
        with open('app.py', 'r') as f:
            app_content = f.read()
        
        required_methods = [
            'on_start_screen_share',
            'on_stop_screen_share',
            'start_screen_share.connect',
            'stop_screen_share.connect'
        ]
        
        missing_methods = []
        for method in required_methods:
            if method not in app_content:
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing in app.py: {', '.join(missing_methods)}")
            return False
        else:
            print("✅ All required methods found in app.py")
            return True
            
    except FileNotFoundError:
        print("❌ app.py not found")
        return False
    except Exception as e:
        print(f"❌ Error checking app.py: {e}")
        return False

def check_media_capture():
    """Check MediaCaptureManager integration."""
    print("🎥 Checking MediaCaptureManager...")
    
    try:
        from client.media_capture import MediaCaptureManager, ScreenCapture
        
        # Create a mock client
        class MockClient:
            def __init__(self):
                self.username = "test"
                self.session_state = {'media_state': {}}
            def _send_tcp_message(self, msg):
                pass
            def set_media_state(self, **kwargs):
                pass
        
        mock_client = MockClient()
        
        # Test MediaCaptureManager
        manager = MediaCaptureManager(mock_client)
        print("✅ MediaCaptureManager created successfully")
        
        # Test ScreenCapture
        screen_capture = ScreenCapture(mock_client)
        if screen_capture.mss:
            print("✅ ScreenCapture initialized successfully")
            
            # Test methods exist
            if hasattr(manager, 'start_screen_share') and hasattr(manager, 'stop_screen_share'):
                print("✅ Screen sharing methods available")
                return True
            else:
                print("❌ Screen sharing methods missing")
                return False
        else:
            print(f"❌ ScreenCapture initialization failed: {screen_capture.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ MediaCaptureManager error: {e}")
        return False

def run_quick_test():
    """Run a quick screen sharing test."""
    print("🧪 Running Quick Test...")
    
    try:
        from client.media_capture import ScreenCapture
        
        class MockClient:
            def __init__(self):
                self.username = "test"
                self.messages = []
            def _send_tcp_message(self, msg):
                self.messages.append(msg)
        
        mock_client = MockClient()
        screen_capture = ScreenCapture(mock_client)
        
        # Test single capture
        jpeg_data = screen_capture.capture_screen()
        if jpeg_data:
            print(f"✅ Single capture test: {len(jpeg_data)} bytes")
        else:
            print("❌ Single capture test failed")
            return False
        
        # Test start/stop
        if screen_capture.start_sharing():
            print("✅ Start sharing test passed")
            import time
            time.sleep(1)  # Let it capture one frame
            screen_capture.stop_sharing()
            print("✅ Stop sharing test passed")
            
            if mock_client.messages:
                print(f"✅ Messages sent: {len(mock_client.messages)}")
                return True
            else:
                print("❌ No messages were sent")
                return False
        else:
            print(f"❌ Start sharing test failed: {screen_capture.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Quick test error: {e}")
        return False

def show_troubleshooting_tips():
    """Show troubleshooting tips."""
    print("\n🔧 Troubleshooting Tips:")
    print("=" * 25)
    print()
    print("If screen sharing still doesn't work:")
    print()
    print("1. **Check System Permissions:**")
    print("   - On macOS: System Preferences > Security & Privacy > Screen Recording")
    print("   - On Windows: Check if app has screen capture permissions")
    print("   - On Linux: Check if running with proper display permissions")
    print()
    print("2. **Check Network Connection:**")
    print("   - Ensure client and server are properly connected")
    print("   - Check firewall settings")
    print("   - Verify TCP port is open")
    print()
    print("3. **Check Application Logs:**")
    print("   - Look for error messages in the console")
    print("   - Check for 'ScreenCapture' or 'screen_frame' related errors")
    print()
    print("4. **Try Manual Test:**")
    print("   - Run: python test_screen_sharing.py")
    print("   - Run: python test_full_screen_sharing.py")
    print()
    print("5. **Check Button State:**")
    print("   - Ensure the screen share button is clickable")
    print("   - Check if error notifications appear")
    print("   - Look at the status indicators in the enhanced status bar")

def main():
    """Main diagnostic function."""
    print("Screen Sharing Diagnostic Tool")
    print("=" * 30)
    print()
    
    all_good = True
    
    # Run all checks
    if not check_dependencies():
        all_good = False
    print()
    
    if not check_permissions():
        all_good = False
    print()
    
    if not check_app_integration():
        all_good = False
    print()
    
    if not check_media_capture():
        all_good = False
    print()
    
    if not run_quick_test():
        all_good = False
    print()
    
    # Show results
    if all_good:
        print("🎉 All Diagnostic Checks Passed!")
        print()
        print("Screen sharing should be working. If it's still not working,")
        print("the issue might be:")
        print("- Network connectivity between client and server")
        print("- GUI button not properly connected")
        print("- Error handling preventing startup")
        print()
        print("Try running the main application and check the console for error messages.")
    else:
        print("❌ Some Diagnostic Checks Failed!")
        print()
        print("Please fix the issues above before trying screen sharing.")
    
    show_troubleshooting_tips()
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())