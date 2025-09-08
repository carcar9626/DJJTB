


def handle_video_tools_with_central_paths(self):
    """Handle video tools submenu with centralized path handling"""
    first_entry = True
    
    while True:
        self.show_video_tools_menu()
        
        if first_entry:
            choice = djj.prompt_choice("\033[93mChoose a Tool\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '0', '00'])
            first_entry = False
        else:
            djj.wait_with_skip(8, "Back to Video Tools")
            choice = djj.prompt_choice("\033[93mChoose another option\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '0', '00'])
        
        # Get paths BEFORE launching script
        if choice in ['1', '2', '3', '4', '5', '6', '7', '8']:
            script_names = {
                '1': 'video_re_encoder',
                '2': 'video_reverse_merge',
                '3': 'video_slideshow_watermark',
                '4': 'video_cropper',
                '5': 'video_group_merger',
                '6': 'video_splitter',
                '7': 'video_speed_changer',
                '8': 'video_frame_extractor'
            }
            
            script_name = script_names[choice]
            
            # Get media input centrally
            media_files = djj.get_centralized_media_input(
                script_name,
                extensions=('.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v')
            )
            
            if not media_files:
                print("\033[93mNo media files selected. Returning to menu.\033[0m")
                continue
            
            # Get output path centrally
            output_path = djj.get_centralized_output_path(script_name)
            
            # Now launch the script - it will read the paths from the centralized system
            module_paths = {
                '1': 'djjtb.media_tools.video_tools.video_re_encoder',
                '2': 'djjtb.media_tools.video_tools.video_reverse_merge',
                '3': 'djjtb.media_tools.video_tools.video_slideshow_watermark',
                '4': 'djjtb.media_tools.video_tools.video_cropper',
                '5': 'djjtb.media_tools.video_tools.video_group_merger',
                '6': 'djjtb.media_tools.video_tools.video_splitter',
                '7': 'djjtb.media_tools.video_tools.video_speed_changer',
                '8': 'djjtb.media_tools.video_tools.video_frame_extractor'
            }
            
            djj.run_script_in_tab(module_paths[choice], self.venv_path, self.project_path)
            
        elif choice == "0":
            break
        elif choice == "00":
            djj.switch_to_terminal_tab("1")
            return "main_menu"
            
def handle_image_tools_with_central_paths(self):
    """Handle image tools submenu with centralized path handling"""
    first_entry = True
    
    while True:
        self.show_image_tools_menu()
        
        if first_entry:
            choice = djj.prompt_choice("\033[93mChoose a Tool\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '0', '00'])
            first_entry = False
        else:
            djj.wait_with_skip(8, "Back to Image Tools")
            choice = djj.prompt_choice("\033[93mChoose another option\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '0', '00'])
        
        # Get paths BEFORE launching script
        if choice in ['1', '2', '3', '4', '5', '6', '7', '8']:
            script_names = {
                
                '1': 'image_converter',
                '2': 'image_strip_padding',
                '3': 'image_flip_rotate',
                '4': 'image_collage_creator',
                '5': 'image_resizer',
                '6': 'image_slideshow_maker',
                '7': 'image_pairing',
                '8': 'image_padder'
            }
            
            script_name = script_names[choice]
            
            # Get media input centrally
            media_files = djj.get_centralized_media_input(
                script_name,
                extensions=('.jpg', '.jpeg', '.webp', '.png', '.bmp', '.tiff')
            )
            
            if not media_files:
                print("\033[93mNo media files selected. Returning to menu.\033[0m")
                continue
            
            # Get output path centrally
            output_path = djj.get_centralized_output_path(script_name)
            
            # Now launch the script - it will read the paths from the centralized system
            module_paths = {
                '1': 'djjtb.media_tools.image_tools.image_converter',
                '2': 'djjtb.media_tools.image_tools.image_strip_padding',
                '3': 'djjtb.media_tools.image_tools.image_flip_rotate',
                '4': 'djjtb.media_tools.image_tools.image_collage_creator',
                '5': 'djjtb.media_tools.image_tools.image_resizer',
                '6': 'djjtb.media_tools.image_tools.image_slideshow_maker',
                '7': 'djjtb.media_tools.image_tools.image_pairing',
                '8': 'djjtb.media_tools.image_tools.image_padder'
            }
            
            djj.run_script_in_tab(module_paths[choice], self.venv_path, self.project_path)
            
        elif choice == "0":
            break
        elif choice == "00":
            djj.switch_to_terminal_tab("1")
            return "main_menu"





