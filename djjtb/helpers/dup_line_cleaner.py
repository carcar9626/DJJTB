input_file = "/Users/home/Documents/Scripts/DJJTB_output/link_scraper/duitang_com/Scraper/2026Apr14_duitang_com.txt"
output_file = "/Users/home/Documents/Scripts/DJJTB_output/link_scraper/duitang_com/Scraper/2026Apr14_duitang_com_NoDUPS.txt"

seen = set()

with open(input_file, "r") as f, open(output_file, "w") as out:
    for line in f:
        if line not in seen:
            out.write(line)
            seen.add(line)