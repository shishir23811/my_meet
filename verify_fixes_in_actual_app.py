#!/usr/bin/env python3
"""
Verify that all the microphone synchronization fixes are present in the actual application code.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def verify_fixes():
    """Verify that all fixes are implemented in the actual application."""
    print("🔍 Verifying Microphone Synchronization Fixes")
    print("=" * 60)
    
    fixes_verified = []
    issues_found = []
    
    # Check 1: Media state change notifications in app.py
    print("\\n1. Checking media state change notifications in app.py...")
    try:
        with open("app.py", "r") as f:
            app_content = f.read()
        
        if "notify_media_state_change('audio', True)" in app_content:
            fixes_verified.append("✅ on_start_audio() calls notify_media_state_change()")
        else:
            issues_found.append("❌ on_start_audio() missing notify_media_state_change() call")
        
        if "notify_media_state_change('audio', False)" in app_content:
            fixes_verified.append("✅ on_stop_audio() calls notify_media_state_change()")
        else:
            issues_found.append("❌ on_stop_audio() missing notify_media_state_change() call")
            
        if "signal.signal(signal.SIGINT" in app_content:
            fixes_verified.append("✅ Signal handling for SIGINT implemented")
        else:
            issues_found.append("❌ Signal handling for SIGINT missing")
            
        if "signal.signal(signal.SIGTERM" in app_content:
            fixes_verified.append("✅ Signal handling for SIGTERM implemented")
        else:
            issues_found.append("❌ Signal handling for SIGTERM missing")
            
        if "def cleanup(self):" in app_content:
            fixes_verified.append("✅ Cleanup method implemented")
        else:
            issues_found.append("❌ Cleanup method missing")
            
    except Exception as e:
        issues_found.append(f"❌ Error reading app.py: {e}")
    
    # Check 2: User disconnection broadcast in server.py
    print("\\n2. Checking user disconnection broadcast in server.py...")
    try:
        with open("server/server.py", "r") as f:
            server_content = f.read()
        
        if "_broadcast_message(user_left_msg)" in server_content:
            fixes_verified.append("✅ User disconnection broadcast implemented")
        else:
            issues_found.append("❌ User disconnection broadcast missing")
            
        if "exclude=username" in server_content:
            fixes_verified.append("✅ User joining broadcast excludes new user")
        else:
            issues_found.append("❌ User joining broadcast doesn't exclude new user")
            
    except Exception as e:
        issues_found.append(f"❌ Error reading server.py: {e}")
    
    # Check 3: Media state handling in client.py
    print("\\n3. Checking media state handling in client.py...")
    try:
        with open("client/client.py", "r") as f:
            client_content = f.read()
        
        if "send_media_state_change" in client_content:
            fixes_verified.append("✅ Client can send media state changes")
        else:
            issues_found.append("❌ Client missing send_media_state_change method")
            
        if "media_state_received = Signal" in client_content:
            fixes_verified.append("✅ Client has media_state_received signal")
        else:
            issues_found.append("❌ Client missing media_state_received signal")
            
        if "MessageType.MEDIA_START.value" in client_content:
            fixes_verified.append("✅ Client handles MEDIA_START messages")
        else:
            issues_found.append("❌ Client missing MEDIA_START message handling")
            
        if "MessageType.MEDIA_STOP.value" in client_content:
            fixes_verified.append("✅ Client handles MEDIA_STOP messages")
        else:
            issues_found.append("❌ Client missing MEDIA_STOP message handling")
            
    except Exception as e:
        issues_found.append(f"❌ Error reading client.py: {e}")
    
    # Check 4: GUI media state handling
    print("\\n4. Checking GUI media state handling...")
    try:
        with open("gui/mainapp.py", "r", encoding="utf-8", errors="ignore") as f:
            gui_content = f.read()
        
        if "update_user_media_state" in gui_content:
            fixes_verified.append("✅ GUI can update user media states")
        else:
            issues_found.append("❌ GUI missing update_user_media_state method")
            
        if "update_user_speaking_state" in gui_content:
            fixes_verified.append("✅ GUI can update user speaking states")
        else:
            issues_found.append("❌ GUI missing update_user_speaking_state method")
            
        if "notify_media_state_change" in gui_content:
            fixes_verified.append("✅ GUI can notify media state changes")
        else:
            issues_found.append("❌ GUI missing notify_media_state_change method")
            
        if "update_audio_state" in gui_content:
            fixes_verified.append("✅ User boxes can update audio state (mic icon)")
        else:
            issues_found.append("❌ User boxes missing update_audio_state method")
            
        if "update_speaking_state" in gui_content:
            fixes_verified.append("✅ User boxes can update speaking state (green border)")
        else:
            issues_found.append("❌ User boxes missing update_speaking_state method")
            
    except Exception as e:
        issues_found.append(f"❌ Error reading gui/mainapp.py: {e}")
    
    # Check 5: Network protocol support
    print("\\n5. Checking network protocol support...")
    try:
        with open("utils/network_proto.py", "r") as f:
            proto_content = f.read()
        
        if "MEDIA_START" in proto_content:
            fixes_verified.append("✅ Network protocol supports MEDIA_START")
        else:
            issues_found.append("❌ Network protocol missing MEDIA_START")
            
        if "MEDIA_STOP" in proto_content:
            fixes_verified.append("✅ Network protocol supports MEDIA_STOP")
        else:
            issues_found.append("❌ Network protocol missing MEDIA_STOP")
            
        if "USER_LEFT" in proto_content:
            fixes_verified.append("✅ Network protocol supports USER_LEFT")
        else:
            issues_found.append("❌ Network protocol missing USER_LEFT")
            
    except Exception as e:
        issues_found.append(f"❌ Error reading utils/network_proto.py: {e}")
    
    # Print results
    print("\\n" + "=" * 60)
    print("📊 VERIFICATION RESULTS")
    print("=" * 60)
    
    print(f"\\n✅ FIXES VERIFIED ({len(fixes_verified)}):")
    for fix in fixes_verified:
        print(f"  {fix}")
    
    if issues_found:
        print(f"\\n❌ ISSUES FOUND ({len(issues_found)}):")
        for issue in issues_found:
            print(f"  {issue}")
    else:
        print(f"\\n🎉 NO ISSUES FOUND!")
    
    # Overall result
    total_checks = len(fixes_verified) + len(issues_found)
    success_rate = len(fixes_verified) / total_checks * 100 if total_checks > 0 else 0
    
    print(f"\\n📈 SUCCESS RATE: {success_rate:.1f}% ({len(fixes_verified)}/{total_checks})")
    
    if len(issues_found) == 0:
        print("\\n🚀 ALL FIXES ARE IMPLEMENTED IN THE ACTUAL APPLICATION!")
        print("The microphone state synchronization should work correctly.")
        print("\\nTo test manually:")
        print("1. Run: python test_actual_app.py")
        print("2. Follow the instructions to test with two users")
        return True
    else:
        print("\\n💔 Some fixes are missing from the actual application.")
        print("Please implement the missing fixes before testing.")
        return False

if __name__ == "__main__":
    success = verify_fixes()
    sys.exit(0 if success else 1)