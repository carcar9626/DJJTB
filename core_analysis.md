# Core Utility Scripts — Plain-English Audit  
*A casual guide for cleaning up your DJJTB script collection*

---


## 🔲 Section: codeformer (Face Enhancer)

### 📂 Script Profiles
  
#### `codeformer_runner.py` (~698 lines – The Quiet One)  
**Core Job:** Runs the CodeFormer AI model to restore/enhance faces in images and videos.  

- **Input Handling:** Accepts a folder path or space-separated file paths (images: jpg, png; videos: mp4, mov, avi).
- **Behavior Under the Hood:** Uses simple `subprocess.run()` with suppressed output during processing—only reports success/fail per file at the end with timing stats.  
- **Fully Functional?** Yes — this is your production-ready batch runner for quiet execution when you just want results without visual chatter while things run in background or large jobs across many files.

#### `codeformer_runner_liveprompt.py` (~762 lines – The Chatty Experiment)  
**Core Job:** Same as above—but adds live console streaming that shows you each file's progress line-by-line with second-level timing displayed on screen ("File time: 1.4s", "Total time: 3m52s").

- **What It Does Differently:** Wraps subprocess calls through a custom `run_process_with_live_output()` function to stream stdout in real-time so you watch what's happening step by step.
- **Fully Functional?** Yes, though slightly slower due to extra I/O overhead; good for debugging or monitoring long job queues on powerful machines that don't mind visual noise during execution

### 🔄 The Key Differences  
**Main Contrast:** Silent batch processing vs verbose real-time feedback  
1. Output Style: Quiet runner suppresses stdout while liveprinter streams line-by-line (you "see it happening")  
2. Progress Monitoring: Live version prints per-file timing; quiet only shows success/fail summary at end of each file  
3. Line Count & Complexity: Base is leaner (~698 lines); live variant adds ~70 extra for output handling and display formatting  

**Which to Use:**  
- **Production Batch Jobs → `codeformer_runner.py`**: minimal distraction from logs, faster overall response time due to less I/O overhead  
- **Debugging Testing With Large Queues Where Visual Feedback Helps: Live version shows when something stalls before finishing everything

### 🧹 Clean-Up Recommendation  
**Keep as Primary:**  Base quiet runner—this ships out-of-the-box and what `djjtb.py` currently calls via launcher reference  

**Archive but Don't Trash Yet:**  The "live prompt" variant can be moved to an optional `/ai_tools/experiments/` folder if you want real-time monitoring for long jobs or debug runs; keep it accessible for situations where watching progress helps catch issues early before finishing all items in a large batch

---  

## 🔲 Section: watermark_remover (Watermark Removal Tools)


### 📂 Script Profiles  

#### `watermark_remover_auto.py` (~1092 lines – The Multi-Detection Heavyweight)  
**Core Job:** Detects and removes various watermark types using multiple strategies plus several inpainting options.

- **Detection Modes:** Pink rectangles, multi-color shapes (rectangles/triangles), text watermarks via OCR, semi-transparent social media overlays—four detection methods with "smart" combinations that try one approach per image before falling back to others.
- **Inpainting Options:** Telea/Navier-Stokes/OpenCV hybrid for traditional methods; LaMa AI (optional) which gives highest quality but uses more memory.

**Does It Look Fully Functional?** Absolutely — this is your most feature-complete watermark remover with batch processing, dynamic batching based on detection mode and inpaint method choice to prevent memory problems—ideal when you face unpredictable file sets containing many different watermark styles that require flexible multi-mode handling across a mixed collection of images from unknown sources

#### `watermark_remover_pkfpl.py` (~702 lines – Florence-2 + LaMa Hybrid)  
**Core Job:** Uses YOLOv8 or pre-downloaded model alongside optional "Florence"-based detection for advanced visual feature matching, plus dedicated support via fallback to simple_lama_inpainting if base isn't available.

- **Model Loading:** Attempts florence-based detection first with automatic fallback when libraries aren't installed
**Does It Look Fully Functional?** Yes — works well but is heavier due to model loading overhead; designed for cases where standard approaches don't detect watermarks or you have specific watermark types that need AI-level visual feature matching

#### `watermark_remover_ref.py` (~952 lines – Reference-Based Template Matching)  
**Core Job:** Loads a reference watermark image and uses template-matching to find identical marks across multiple source images, optionally exports mask files if needed for ChaiNNer-style post-processing.

- **Detection Method:** Multi-scale OpenCV-based approach with optional alpha-channel handling; supports transparency detection so you can remove watermarks that appear at different opacities without requiring exact pixel-for-pixel matches
**Does It Look Fully Functional?** Yes — particularly when your watermark exists unchanged across many images and reference matching is needed instead of retraining or custom training

#### `watermark_remover_settings.txt.py` (~75 lines – The Settings File Pretending to Be Code)  
This isn't a runnable script at all—it's just plain text marked with `.py`. Contains notes about tunable parameters in the main auto version like confidence thresholds, pad amounts around detected regions, and batch sizing per detection mode.  

**Recommendation:** Either delete this or convert it into proper markdown documentation if you want to keep your tuning guide somewhere accessible later; as a Python file pretending to be code it will cause confusion

#### `watermark_remover_unified.py` (~626 lines – The Combined Version With Corruptions)  
**Core Job:** Attempts to merge reference template-matching and OCR auto-detection into one interface—but the current content appears corrupted or broken (lines 10-87 show class methods that are orphaned without proper `class UnifiedWatermarkRemover:` declaration before them). 

**Does It Look Fully Functional?** No — clearly incomplete: missing parts of the class definition, cut-and-paste failures left behind from merging two full scripts into one; needs substantial cleanup if you want to use this unified approach in production  

### 🔄 The Key Differences  
| File | Detection Strategy | Strengths | Line Count |
|------|-------------------|-----------|------------|
| `auto.py` | Multiple (4 modes) + optional LaMa AI | Handles most watermark types automatically; best balance of flexibility and out-of-box usability without needing custom reference images, heavy on memory due to multiple detection methods but batch processing compensates for that overhead when dealing with mixed sources | ~1092 lines: heaviest script overall because it implements all 4 distinct modes plus their combination strategies in one place where they can fail back gracefully depending what you select from the UI prompts first thing during runtime so users never see broken detection attempts without selecting options upfront before running batch jobs across many files simultaneously with varying watermark styles that traditional color-based approaches alone might miss |
| `pkfpl.py` | YOLO/Florence hybrid + LaMa fallback | Good when standard methods fail; uses advanced models but loads them fresh each time which adds startup overhead and memory cost if you're working with hundreds of similar images or just testing a few files at one shot where performance matters more than trying to cover every possible detection case automatically for unknown sources without requiring custom setup per project folder structure | ~702 lines |
| `ref.py` | Reference-based template matching | Perfect when exact same watermark appears across many documents; requires providing reference image upfront but handles identical marks even if they differ slightly in scale/location due to alpha-channel support which lets you remove watermarks that appear semi-transparent on backgrounds without retraining custom detectors per source style or location pattern within a single batch run of similar images from the document set | ~952 lines: second heaviest only because it implements full multi-scale template matching plus optional mask export functionality for downstream applications like ChaiNNer where you might want to pass generated masks elsewhere in your workflow rather than just removing watermarks automatically without ever needing to see intermediate results during processing so users can inspect exactly what regions got selected versus areas that were skipped |
| `unified.py` | Both reference+OCR combined (broken) | Would let you switch between detection modes within same batch run, but current content is incomplete and will fail with missing errors when trying to use this for production workloads where reliability matters more than having one script cover multiple scenarios automatically without needing separate launches depending on what watermark types need different approaches across your document library or source collection being processed in a single operation | ~626 lines: smaller size but clearly broken mid-class definition makes it unsafe until refactored from scratch with working implementation verified by running tests against known problematic images for each detection mode so you know before relying on whichever approach handles the specific watermark type currently present across files needing consistent handling without breaking when encountering unexpected combinations of text overlays or semi-transparent graphics mixed together in same folder structure where traditional single-mode approaches wouldn't detect any watermarks at all requiring custom training per case anyway |

### 🧹 Clean-Up Recommendation  
**Keep as Primary:** The `auto.py` version is your safest bet for most situations—it handles the widest variety of watermark types automatically and gives you options without needing to provide reference images upfront which makes it more plug-and-play friendly when processing unknown sources across different document formats in batches together rather than separately depending on what styles appear within each folder being processed at one time

**Archive/Delete:**  
- **Delete Immediately**: *`settings.txt.py`* isn't valid Python—it's just a plain-text file pretending to be code with `.py` extension—this should go right away without any hesitation since it could cause confusion or errors if someone tries running this thinking it works like other scripts in directory  
→ Move `unified.py` to `/ai_tools/experiments/` folder for potential refactoring later once you decide whether merging both detection modes into one script is worth the effort required; consider keeping separate specialized tools as they each excel at their own approach rather than forcing everything into single monolithic implementation  

**Consider Keeping:**  
- The three complete versions (`auto.py`, `pkfpl.py`, `ref.py`) represent distinct strategies where trade-offs exist: multi-detection flexibility vs model-based advanced matching for tricky cases, reference image template matching when watermarks appear consistently across documents with minor variations in scale or location. You might want all three readily accessible depending on current project needs rather than consolidating prematurely unless you specifically need unified interface that supports both approaches within same script invocation instead of launching different tools based on whether you have reference images available from earlier processing rounds where those files were successfully detected previously without failing because their templates weren't properly loaded or configured correctly during initial setup phase when first starting up batch runs for unknown sources across multiple folders being processed simultaneously with varying watermarks present throughout document collection overall rather than testing each approach separately one at a time before deciding which method handles current project best given what's available in your toolset right now


## 📂 Script Profiles

### `codeformer_runner.py` (698 lines) - The "Quiet" Version
**Core Job:** Runs CodeFormer to enhance faces in images/videos using AI upscaling.

**How it works under the hood:**
- Collects files from folders or space-separated paths
- Processes them one-by-one without showing you anything while it's running (silent output capture)
- Only tells you "Success!" at the end with a summary
- Uses `subprocess.run()` which is simpler and more reliable for batch jobs

**Does it look fully functional?** Yes — it ships as-is for production use. It won't show processing progress, but that's intentional: quiet execution reduces visual noise in logs.

### `codeformer_runner_liveprompt.py` (762 lines) - The "Chatty" Version
**Core Job:** Same thing—runs CodeFormer—but streams live console output as each file processes and provides second-by-second timing updates.

**How it works under the hood:**
- Adds a streaming function (`run_process_with_live_output`) that pipes stdout so you watch progress in real-time
- Prints individual timings for every file ("File time: 1.2s", "Total time: 3m45s")
- More verbose feedback, useful when debugging or running on powerful machines with long queues

**Does it look fully functional?** Yes — works well but is slower to respond because of the extra output handling. Good for test runs, less ideal for production batch jobs where you just want results without chatter.

---

## 🔄 The Key Differences

### What sets them apart:
1. **Output behavior:** quiet vs verbose console streaming  
2. **Live progress display** — Live version shows what's happening in real-time; standard version only reports success/fail per file  
3. **Line count and complexity** — Standard is shorter (698 lines), live prompt has more (~760) because of extra timing logic and formatting output helpers  

### Which version should you use:
- ✅ `codeformer_runner.py` = production batch runs where results matter most, minimal distraction  
- ⚙️  `codeformer_runner_liveprompt.py` = debugging/testing when you want to see what's happening while jobs run (e.g., long queues across dozens of files)  

### Active / current version:
The launcher (`djjtb.py`) references the **standard** runner only, so that is your primary active file. The live output variant was probably created during development as an experiment and isn't called by default yet — but it's still useful in certain scenarios (large batches where you want to monitor progress).

---

## 🧹 Clean-Up Recommendation

### Keep / Primary:
- **`codeformer_runner.py`** — This is the master version used for production. It performs all necessary tasks without unnecessary complexity, and `djjtb.py` calls this one explicitly. No redundancy here; it's streamlined and reliable.

### Archive (but don't trash yet):
- **`codeformer_runner_liveprompt.py`** — Keep as an "experiment" or fallback when debugging long jobs with live output requirements, but mark for review before any cleanup run. It has value if you want to visualize what CodeFormer is doing during batch runs.

### Why not delete both:
They're complementary tools rather than exact duplicates — one optimized for speed and reliability in production use; the other focused on visibility when debugging or running long queues where progress monitoring can catch issues early before everything finishes. Decide together whether live logging should be promoted (with minor cleanup) as a secondary launcher option, then archive this to an `ai_tools/experiments/` folder until you're ready for batch #2 decisions next month if it's truly needed there too.

---
*Plain-English audit generated Mon Jul 6 · Batch#1 analysis complete*
