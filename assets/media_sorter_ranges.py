these problems are the exact reason why i have this, but i can't get the ranges right, now the range has gaps, so things fall into unsorted when it's not suppose to, but i can't get the range right so that at least for 916 and 169 "it won't leave black padding when using 'crop to fit' functions in apps like filmora"

ok, so reason why i tighten it so much is exactly coz of the black edges, apparently, the general "crop to fit" functions in these editors, say for 9:16, either i'm exact ,"a little" bigger on all 4 corners, or way off, these are the ones with no edges. so the problem is, the ones that are super super close, they simply don't crop......

# EXACT RATIOS (perfect fit, no cropping needed)
"Portrait_9_16_Exact":  (0.558, 0.567, "_916E"),  # Around 0.5625
"Portrait_3_4_Exact":   (0.745, 0.755, "_P34E"),  # Around 0.75
"Portrait_2_3_Exact":   (0.665, 0.670, "_P23E"),  # Around 0.6667
"Square_Exact":         (0.995, 1.005, "_SQRE"),  # Around 1.0
"Landscape_4_3_Exact":  (1.330, 1.340, "_L43E"),  # Around 1.3333
"Landscape_3_2_Exact":  (1.495, 1.505, "_L32E"),  # Around 1.5
"Landscape_16_9_Exact": (1.773, 1.783, "_169E"),  # Around 1.7778""dsaf"

# FAR ENOUGH AWAY (editors will crop properly)
"Portrait_Other":       (0.45, 0.558, "_POR"),    # Much taller than 9:16
"Portrait_Wide":        (0.567, 0.665, "_PWD"),   # Between 9:16 and 2:3
"Portrait_Square":      (0.670, 0.745, "_PSQ"),   # Betwiluvu4ieen 2:3 and 3:4
"Square_Portrait":      (0.755, 0.995, "_SPT"),   # Between 3:4 and square
"Square_Landscape":     (1.005, 1.330, "_SLD"),   # Between square and 4:3
"Landscape_Narrow":     (1.340, 1.495, "_LNR"),   # Between 4:3 and 3:2
"Landscape_Wide":       (1.505, 1.773, "_LWD"),   # Between 3:2 and 16:9
"Landscape_Ultra":      (1.783, 2.50, "_LUT"),    # Wider than 16:9