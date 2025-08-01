project main script @ /Users/home/Documents/Scripts/DJJTB/djjtb.py
https://gist.githubusercontent.com/carcar9626/aa4d48c97de6eb1577b3fc340a2f4b31/raw/c035be16810d6940ad7f06ceccfec6359f7443ab/djjtb.py

utils @ /Users/home/Documents/Scripts/DJJTB/djjtp/utils.py (ALWAYS 'import djjtb.utils as djj')
https://gist.githubusercontent.com/carcar9626/12d82b896c5a1acd76baaef268b79ad5/raw/c537c16eac0a5437f61abff2959366b52fa27971/utils.py

reference for input mode, input/output handling, prompt inputhandling, headers, formats, colours, escapes, etc...
https://gist.githubusercontent.com/carcar9626/f4d6db722ea653cf3910bb6e7fe92c6a/raw/499e905718ae30ad6f456c7770ce853a35698618/video_group_merger.py

script that need fix:
https://gist.githubusercontent.com/carcar9626/b6a228daab7105f6881b1b2714d28557/raw/eb94e3ad5add1fb7e774081e36417bfb058f2591/metadata_injector.py
https://gist.githubusercontent.com/carcar9626/8059f5b0cdfd2c8faa860c5c09e6ffd0/raw/46a11155f01af4909349c018558bdc00398dbec8/media_metadata_identifier.py

so as you can see, i have two metadata tools that i want to combine and adapt it to the references mentioned above (this one has its own subfolder and tagging output so we of course keep those). there're a few problems, and fixes (this context assumes the "adaptation" is completed):
1. prompt if i want to inject "fake" metadata when stripping is completed
2. if possible, can try to be more creative with the "fake", i don't need a whole randomizer, but bunch of random choices would be nice or randomized from a bunch of generic words that makes sense or something better you might suggest, doesn't really matter, just to trick some online i2v generator that constantly interupt my workflow coz my image has "no valid metadata"
3. the identifier.....when you made this, i think we didn't go "deep" enough, what i meant wasn't just telling me what the file extension is, i mean i always come across say an image file that has no extension or wrong extension, i want to identify those. i don't know a lot about coding at all so i can't gauge how complicated this is, if it is, my priority is the metadata function
if needed, please use as much djj function as possible but even for the smallest trade off, please write a new function if needed then suggests if it's worth to add to utils.
Everything besides its actual function should follow the reference, input/output, aesthetic etc. thank you




, as you can see, the script now breaks after i input number of collages, besides this i believe the background handling mentioned above has problems as well. while fixing this, i'd like to add square and 640*1080 along with just horizontal and vertical output. from the according to the original logic:
https://gist.githubusercontent.com/carcar9626/27cefa5a994aa1920b40dcf487036a80/raw/66d6dd8346c6fe6086d5197bd9d304456e9981d3/image_collage_creator.py

parameters for newly added options:
Square: if source is square then 2x2, if source is portrait then 2 x 1, if source is landscape then 1 x 2
1280*1080: if source is square then 1 x 2, if source is portrait then 2 x 2, if source is landscape then 1 x 3

However my main goal is to fix the script so at least it works first. Everything besides its actual function should follow the referene, input/output, aesthtic etc, use anything you can in utils, but even for the smallest trade off, please write a new function if needed then suggests if it's worth to add to utils.
There's a lot of information here, please make sure you understand 100% before updating the script. the Square and 1280 * 1080 i mentioned above should be clear after you read my script. if there're anything unclear or suggestions, i'm all ears. this collage script has always been part of the djjtb project, in fact it was the very first media script i worked on. but hey things break...lol right also, as you can see in the reference, the input mode is inserted, please try to do the same to this one as well.



/Users/home/Documents/Scripts/DJJTB/djjtb/quick_tools/Linkgrabber


i want to add a media tool to this project, it should have the similar structure, flows and aesthetics as the reference besides its actual function. i want a python script to batch remove all metadata from videos or image (best if it can process combined inputs, but if too complicated, your call, can insert prompt after subfolder or wherever you deem necessary). if in multi file mode, i will manually control the load. a prompt added in between to ask if replace or create new, if new output path = ...input path/Output/meta_stripped (in case of multifiles input, can just use each input parent as input path, i want them nested nearby its source). output filename: (input file name)_no_meta.xxx

this was function one, if not complicated, i want to add another option (at beginning of script 1. Metadata Stripper 2. Media Files ID). with same structure, i drop few files/or a folder, just identify the file type/extensions. option to export to csv after (nested in input path, in case of multi files the parent of first file), filename if folder mode, input path_ID.csv

i think you can tell from the reference for the escape etc..use djj.prompt_choice for defaults. remember to import djjtb.utils as djj, i track them with a simple script. use utils as much as you can but please write new function even for the smallest comprise and suggest if it's worth to insert into utils.

i don't know much about coding, but i've been working on this project alongside you in other chats and gpt for a while now. let me know if sending you context like this is a good way or too much to process in one message. dont worry about implementing utils and the main script, i will handle them, please focus on acing this new function. it will be nested under djjtb.media_tools alongside media sorter and playlist gen
thank you very much



