import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime
from gradio_client import Client
from gradio_client.utils import handle_file
# ----- Prevent multiple concurrent executions -----
import psutil

LOCK_FILE = "/root/speech2text/stream_onlineradio/transcribewave/tmp/transcription_script.lock"

def is_already_running():
    """Check if another instance of this script is already running."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())

            # Check if PID is still active
            if psutil.pid_exists(pid):
                print(f"Another instance is already running with PID {pid}. Exiting.")
                return True

        except Exception:
            # If error reading PID, overwrite the file
            pass

    # Write our PID into lock file
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    return False


# Call the check
if is_already_running():
    sys.exit(0)
# ---------------------------------------------------


# Configuration - Multiple Hugging Face Spaces (Round-Robin)
HF_SPACES = [
    "https://dmajor007-audiotranscription.hf.space",
    "https://dmajor007-audiotranscription1-hfrepo.hf.space",
]

# Directories
RJR_RECORDINGS_DIR = "/root/speech2text/stream_onlineradio/transcribewave/recordings_RJR"
POWER106_RECORDINGS_DIR = "/root/speech2text/stream_onlineradio/transcribewave/recordings_power106"
RJR_TRANSCRIPTS_DIR = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_RJR"
POWER106_TRANSCRIPTS_DIR = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_power106"
RJR_COMPLETED_DIR = "/root/speech2text/stream_onlineradio/transcribewave/transcription_completed_RJR"
POWER106_COMPLETED_DIR = "/root/speech2text/stream_onlineradio/transcribewave/transcription_completed_power106"
LOG_DIR = "/root/speech2text/stream_onlineradio/transcribewave/logs"

# Processing parameters
MAX_FILES_PER_RUN = 30  # Limit files per cron run to avoid timeouts

class HFSpacePool:
    """Manages multiple HF Spaces in round-robin fashion"""
    
    def __init__(self, space_urls, log_file=None):
        self.space_urls = space_urls
        self.clients = {}
        self.current_index = 0
        self.log_file = log_file
        self.failed_spaces = set()
        
    def connect_all(self):
        """Connect to all HF Spaces"""
        log_message(f"🤗 Connecting to {len(self.space_urls)} Hugging Face Space(s)...", self.log_file)
        
        for i, url in enumerate(self.space_urls):
            try:
                log_message(f"   [{i+1}/{len(self.space_urls)}] Connecting to: {url}", self.log_file)
                client = Client(url)
                self.clients[url] = client
                log_message(f"   ✅ Connected successfully", self.log_file)
            except Exception as e:
                log_message(f"   ❌ Failed to connect: {e}", self.log_file)
                self.failed_spaces.add(url)
        
        available_count = len(self.clients)
        if available_count == 0:
            log_message("❌ No HF Spaces available!", self.log_file)
            return False
        
        log_message(f"✅ {available_count}/{len(self.space_urls)} Space(s) available", self.log_file)
        return True
    
    def get_next_client(self):
        """Get next client in round-robin fashion"""
        if not self.clients:
            return None
        
        # Get list of available URLs (not failed)
        available_urls = [url for url in self.space_urls if url in self.clients and url not in self.failed_spaces]
        
        if not available_urls:
            return None
        
        # Round-robin selection
        url = available_urls[self.current_index % len(available_urls)]
        self.current_index += 1
        
        return self.clients[url], url
    
    def mark_failed(self, url):
        """Mark a space as temporarily failed"""
        self.failed_spaces.add(url)
        log_message(f"⚠️  Marked as failed: {url}", self.log_file)
        
        # If all spaces failed, reset the failed set to try again
        available_count = len([u for u in self.space_urls if u in self.clients and u not in self.failed_spaces])
        if available_count == 0:
            log_message("⚠️  All spaces failed, resetting...", self.log_file)
            self.failed_spaces.clear()

def log_message(message, log_file=None):
    """Log message to console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    if log_file:
        try:
            with open(log_file, 'a') as f:
                f.write(log_msg + "\n")
        except Exception as e:
            print(f"Warning: Could not write to log: {e}")

def extract_timestamp_from_filename(filename):
    """Extract timestamp from WAV filename for sorting"""
    # Expected format: StationName_recording_YYYYMMDD_HHMMSS_segXXX.wav
    # Example: RJR_recording_20241122_140000_seg001.wav
    match = re.search(r'(\d{8}_\d{6})', filename)
    if match:
        return match.group(1)
    return None

def get_wav_files_sorted(directory):
    """Get all WAV files sorted by timestamp in filename"""
    wav_files = []
    
    try:
        for file in Path(directory).glob("*.wav"):
            # Skip .tmp files
            if file.suffix == '.tmp' or file.name.endswith('.wav.tmp'):
                continue
            
            timestamp = extract_timestamp_from_filename(file.name)
            if timestamp:
                wav_files.append((timestamp, str(file)))
        
        # Sort by timestamp
        wav_files.sort(key=lambda x: x[0])
        
        # Return just the file paths
        return [f[1] for f in wav_files]
    
    except Exception as e:
        print(f"Error scanning directory {directory}: {e}")
        return []

def get_transcript_path(wav_file, transcripts_dir):
    """Generate transcript path from WAV file path"""
    wav_name = Path(wav_file).stem
    return os.path.join(transcripts_dir, f"{wav_name}_transcript.txt")

def is_already_transcribed(wav_file, transcripts_dir):
    """Check if WAV file has already been transcribed"""
    transcript_path = get_transcript_path(wav_file, transcripts_dir)
    return os.path.exists(transcript_path)

def transcribe_single_file(hf_pool, wav_file, transcript_path, completed_dir, log_file):
    """Transcribe a single WAV file using round-robin HF Spaces"""
    wav_name = Path(wav_file).name
    log_message(f"🎤 Transcribing: {wav_name}", log_file)
    
    max_retries = len(HF_SPACES)
    
    for attempt in range(max_retries):
        try:
            # Get next client in round-robin
            result = hf_pool.get_next_client()
            if result is None:
                log_message(f"   ❌ No HF Spaces available", log_file)
                return False
            
            client, space_url = result
            space_name = space_url.split('//')[1].split('.')[0] if '//' in space_url else space_url
            
            if attempt > 0:
                log_message(f"   🔄 Retry {attempt + 1}/{max_retries} using: {space_name}", log_file)
            else:
                log_message(f"   🌐 Using space: {space_name}", log_file)
            
            # Call HF Space API
            text = client.predict(handle_file(wav_file))
            
            if not text:
                text = "[Silence or unclear audio]"
            
            # Save transcript
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"WAV File Transcription\n")
                f.write(f"Source: {wav_name}\n")
                f.write(f"HF Space: {space_url}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(text)
                f.write("\n")
            
            log_message(f"   ✅ Saved to: {Path(transcript_path).name}", log_file)
            
            # Move WAV file to completed directory
            try:
                os.makedirs(completed_dir, exist_ok=True)
                destination = os.path.join(completed_dir, wav_name)
                shutil.move(wav_file, destination)
                log_message(f"   📦 Moved to: {completed_dir}/{wav_name}", log_file)
            except Exception as e:
                log_message(f"   ⚠️  Could not move file: {e}", log_file)
                # Still consider it successful since transcription worked
            
            return True
            
        except Exception as e:
            log_message(f"   ⚠️  Transcription failed with {space_name}: {e}", log_file)
            hf_pool.mark_failed(space_url)
            
            # Continue to next retry
            continue
    
    # All retries exhausted
    log_message(f"   ❌ Transcription failed after {max_retries} attempts", log_file)
    return False

def process_directory(station_name, recordings_dir, transcripts_dir, completed_dir, hf_pool, log_file):
    """Process all untranscribed WAV files in a directory"""
    log_message("=" * 60, log_file)
    log_message(f"📻 Processing {station_name}", log_file)
    log_message(f"📂 Recordings: {recordings_dir}/", log_file)
    log_message(f"📄 Transcripts: {transcripts_dir}/", log_file)
    log_message(f"📦 Completed: {completed_dir}/", log_file)
    log_message("-" * 60, log_file)
    
    # Create directories
    os.makedirs(transcripts_dir, exist_ok=True)
    os.makedirs(completed_dir, exist_ok=True)
    
    # Get all WAV files sorted by timestamp
    wav_files = get_wav_files_sorted(recordings_dir)
    
    if not wav_files:
        log_message("⚠️  No WAV files found", log_file)
        return 0, 0
    
    log_message(f"📋 Found {len(wav_files)} WAV file(s)", log_file)
    
    # Filter out already transcribed files
    files_to_process = []
    for wav_file in wav_files:
        if not is_already_transcribed(wav_file, transcripts_dir):
            files_to_process.append(wav_file)
    
    if not files_to_process:
        log_message("✅ All files already transcribed", log_file)
        return 0, 0
    
    log_message(f"📝 Files to transcribe: {len(files_to_process)}", log_file)
    
    # Limit number of files per run
    if len(files_to_process) > MAX_FILES_PER_RUN:
        log_message(f"⚠️  Limiting to {MAX_FILES_PER_RUN} files per run", log_file)
        files_to_process = files_to_process[:MAX_FILES_PER_RUN]
    
    log_message("-" * 60, log_file)
    
    # Process each file
    successful = 0
    failed = 0
    
    for i, wav_file in enumerate(files_to_process, 1):
        log_message(f"[{i}/{len(files_to_process)}] Processing...", log_file)
        transcript_path = get_transcript_path(wav_file, transcripts_dir)
        
        if transcribe_single_file(hf_pool, wav_file, transcript_path, completed_dir, log_file):
            successful += 1
        else:
            failed += 1
    
    log_message("-" * 60, log_file)
    log_message(f"📊 {station_name} Results: {successful} successful, {failed} failed", log_file)
    log_message("=" * 60, log_file)
    
    return successful, failed

def main():
    # Set up logging
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"transcription_{datetime.now().strftime('%Y%m%d')}.log")
    
    log_message("=" * 60, log_file)
    log_message("📻 Batch WAV Transcription Service (Multi-Space)", log_file)
    log_message(f"🌐 HF Spaces: {len(HF_SPACES)} configured", log_file)
    log_message("=" * 60, log_file)
    
    # Initialize HF Space pool
    hf_pool = HFSpacePool(HF_SPACES, log_file)
    
    # Connect to all spaces
    if not hf_pool.connect_all():
        log_message("❌ Cannot proceed without any available HF Spaces", log_file)
        return 1
    
    total_successful = 0
    total_failed = 0
    
    # Process RJR recordings
    if os.path.exists(RJR_RECORDINGS_DIR):
        successful, failed = process_directory(
            "RJR", 
            RJR_RECORDINGS_DIR, 
            RJR_TRANSCRIPTS_DIR,
            RJR_COMPLETED_DIR,
            hf_pool, 
            log_file
        )
        total_successful += successful
        total_failed += failed
    else:
        log_message(f"⚠️  Directory not found: {RJR_RECORDINGS_DIR}", log_file)
    
    # Process Power106 recordings
    if os.path.exists(POWER106_RECORDINGS_DIR):
        successful, failed = process_directory(
            "Power106", 
            POWER106_RECORDINGS_DIR, 
            POWER106_TRANSCRIPTS_DIR,
            POWER106_COMPLETED_DIR,
            hf_pool, 
            log_file
        )
        total_successful += successful
        total_failed += failed
    else:
        log_message(f"⚠️  Directory not found: {POWER106_RECORDINGS_DIR}", log_file)
    
    # Final summary
    log_message("=" * 60, log_file)
    log_message("✅ Batch transcription complete", log_file)
    log_message(f"📊 Total successful: {total_successful}", log_file)
    if total_failed > 0:
        log_message(f"⚠️  Total failed: {total_failed}", log_file)
    log_message("=" * 60, log_file)
    
    return 0





if __name__ == "__main__":
    exit_code = main()

    # Cleanup lock file on exit
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except:
        pass

    sys.exit(exit_code)
