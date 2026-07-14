#!/bin/bash
# install_grabbers.sh
# Run this once to set up auto-launch for Link Grabber and Path Grabber
# Usage: bash install_grabbers.sh

set -e  # Stop on any error

LAUNCHERS_DIR="$HOME/Documents/Scripts/DJJTB/launchers"
PLIST_DIR="$HOME/Library/LaunchAgents"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"  # folder where this script lives

echo ""
echo "======================================================"
echo "  DJJTB Grabbers — Auto-Launch Installer"
echo "======================================================"
echo ""

# ── Step 1: Create launchers folder ──────────────────────
echo "📁 Creating launchers folder..."
mkdir -p "$LAUNCHERS_DIR"

# ── Step 2: Compile AppleScripts to .scpt ────────────────
# LaunchAgents can't run .applescript text files directly,
# they need compiled .scpt binaries. osacompile does this.

echo "🍎 Compiling Link Grabber AppleScript..."
osacompile -o "$LAUNCHERS_DIR/launch_link_grabber.scpt" \
    "$SCRIPT_DIR/launch_link_grabber.applescript"

echo "🍎 Compiling Path Grabber AppleScript..."
osacompile -o "$LAUNCHERS_DIR/launch_path_grabber.scpt" \
    "$SCRIPT_DIR/launch_path_grabber.applescript"

echo "✅ AppleScripts compiled."
echo ""

# ── Step 3: Install plist files ──────────────────────────
echo "📋 Installing LaunchAgent plists..."
cp "$SCRIPT_DIR/com.djjtb.link-grabber.plist" "$PLIST_DIR/"
cp "$SCRIPT_DIR/com.djjtb.path-grabber.plist" "$PLIST_DIR/"

# Set correct permissions (LaunchAgent plists are picky about this)
chmod 644 "$PLIST_DIR/com.djjtb.link-grabber.plist"
chmod 644 "$PLIST_DIR/com.djjtb.path-grabber.plist"

echo "✅ Plists installed."
echo ""

# ── Step 4: Load the agents (takes effect immediately) ───
echo "⚡ Loading LaunchAgents..."

# Unload first in case they were already loaded (avoids duplicate errors)
launchctl unload "$PLIST_DIR/com.djjtb.link-grabber.plist" 2>/dev/null || true
launchctl unload "$PLIST_DIR/com.djjtb.path-grabber.plist" 2>/dev/null || true

launchctl load "$PLIST_DIR/com.djjtb.link-grabber.plist"
launchctl load "$PLIST_DIR/com.djjtb.path-grabber.plist"

echo "✅ LaunchAgents loaded."
echo ""

echo "======================================================"
echo "  Done! Both grabbers will now auto-launch at login."
echo ""
echo "  To test right now without rebooting:"
echo "  launchctl start com.djjtb.link-grabber"
echo "  launchctl start com.djjtb.path-grabber"
echo ""
echo "  To uninstall later, run: bash uninstall_grabbers.sh"
echo "======================================================"
echo ""
