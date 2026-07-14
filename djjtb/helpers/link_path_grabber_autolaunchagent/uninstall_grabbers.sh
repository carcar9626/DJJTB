#!/bin/bash
# uninstall_grabbers.sh
# Removes auto-launch for both grabbers cleanly

PLIST_DIR="$HOME/Library/LaunchAgents"

echo ""
echo "======================================================"
echo "  DJJTB Grabbers — Uninstaller"
echo "======================================================"
echo ""

echo "⏹  Unloading LaunchAgents..."
launchctl unload "$PLIST_DIR/com.djjtb.link-grabber.plist" 2>/dev/null || echo "   (link-grabber wasn't loaded)"
launchctl unload "$PLIST_DIR/com.djjtb.path-grabber.plist" 2>/dev/null || echo "   (path-grabber wasn't loaded)"

echo "🗑  Removing plist files..."
rm -f "$PLIST_DIR/com.djjtb.link-grabber.plist"
rm -f "$PLIST_DIR/com.djjtb.path-grabber.plist"

echo ""
echo "✅ Done. Grabbers will no longer auto-launch at login."
echo "   The grabber scripts themselves are untouched."
echo "======================================================"
echo ""
