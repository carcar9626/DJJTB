-- launch_link_grabber.applescript
-- Auto-launches Link Grabber in a Terminal window at login
-- Place the compiled version in ~/Documents/Scripts/DJJTB/launchers/

set venvActivate to "source ~/Documents/Scripts/DJJTB/venv/bin/activate"
set projectPath to "/Users/home/Documents/Scripts/DJJTB"
set runCmd to "python3 -m djjtb.quick_tools.link_grabber"
set fullCmd to venvActivate & "; cd " & projectPath & "; " & runCmd

-- Wait for desktop and Terminal to be fully ready after boot
delay 20

tell application "Terminal"
	activate
	delay 2
	do script fullCmd
	delay 2
	try
		set current settings of front window to settings set "LinkGrabber"
	end try
	delay 0.5
	set bounds of front window to {1930, 1650, 2950, 1890}
end tell
