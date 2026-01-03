import os
import sys
import re
import time
import shutil
from pathlib import Path
from datetime import datetime
from gradio_client import Client
from gradio_client.utils import handle_file
# ----- Prevent multiple concurrent executions -----
import psutil


LOCK_FILE = "/root/speech2text/stream_onlineradio/transcribewave/tmp/transcription_script_rjr1.lock"
LOCK_CHECK_INTERVAL = 15  # seconds to wait before checking lock again
MAX_LOCK_WAIT_TIME = 300  # maximum time to wait for lock (5 minutes)

# Set up logging
LOG_DIR = "/root/speech2text/stream_onlineradio/transcribewave/logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"transcription_{datetime.now().strftime('%Y%m%d')}.log")

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



def is_already_running():
    """
    Check if another instance of this script is already running.
    If locked, wait and retry until lock is released or timeout.
    """
    wait_time = 0

    while wait_time < MAX_LOCK_WAIT_TIME:
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, "r") as f:
                    pid_str = f.read().strip()

                if not pid_str:
                    # Empty lock file, treat as stale
                    print("Found empty lock file for RJR1. Removing...")
                    try:
                        os.remove(LOCK_FILE)
                    except:
                        pass
                    break

                try:
                    pid = int(pid_str)
                except ValueError:
                    # Invalid PID in lock file, treat as stale
                    print(f"Found invalid PID in lock file for RJR1: '{pid_str}'. Removing...")
                    try:
                        os.remove(LOCK_FILE)
                    except:
                        pass
                    break

                # Check if PID is still active
                if psutil.pid_exists(pid):
                    if wait_time == 0:
                        print(f"Another instance is already running for RJR1 with PID {pid}.")
                        print(f"Waiting for lock for RJR1 to be released (checking every {LOCK_CHECK_INTERVAL}s)...")
                    else:
                        print(f"Still waiting(RJR1)... ({wait_time}s elapsed)")

                    # Wait before checking again
                    time.sleep(LOCK_CHECK_INTERVAL)
                    wait_time += LOCK_CHECK_INTERVAL
                    continue
                else:
                    # PID no longer exists, stale lock file
                    print(f"Found stale lock file for RJR1 (PID {pid} not running). Removing...")
                    try:
                        os.remove(LOCK_FILE)
                    except:
                        pass
                    break

            except IOError as e:
                # File read error - maybe file was deleted or permissions issue
                print(f"Error reading lock file for RJR1: {e}")
                if wait_time == 0:
                    print(f"Waiting and will retry(RJR1)... (checking every {LOCK_CHECK_INTERVAL}s)")

                # Wait and retry instead of breaking
                time.sleep(LOCK_CHECK_INTERVAL)
                wait_time += LOCK_CHECK_INTERVAL
                continue

            except Exception as e:
                # Unexpected error
                print(f"Unexpected error checking lock for RJR1: {e}")
                if wait_time == 0:
                    print(f"Waiting and will retry(RJR1)... (checking every {LOCK_CHECK_INTERVAL}s)")

                # Wait and retry instead of breaking
                time.sleep(LOCK_CHECK_INTERVAL)
                wait_time += LOCK_CHECK_INTERVAL
                continue
        else:
            # No lock file exists
            break

    # Check if we timed out
    if wait_time >= MAX_LOCK_WAIT_TIME:
        print(f"Timeout: Lock not released for RJR1 after {MAX_LOCK_WAIT_TIME}s. Exiting.")
        return True

    # Acquire lock by writing our PID
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)

        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        print(f"Lock acquired for RJR1 (PID {os.getpid()})")
        return False
    except Exception as e:
        print(f"Error acquiring lock for RJR1: {e}")
        return True


# Call the check
if is_already_running():
    sys.exit(0)
# ---------------------------------------------------


# Configuration
HF_SPACE_URL = "https://dmajor007-audiotranscription.hf.space"

# Directories
RJR_RECORDINGS_DIR = "/root/speech2text/stream_onlineradio/transcribewave/recordings_RJR"
POWER106_RECORDINGS_DIR = "/root/speech2text/stream_onlineradio/transcribewave/recordings_power106"
RJR_TRANSCRIPTS_DIR = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_RJR"
POWER106_TRANSCRIPTS_DIR = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_power106"
RJR_COMPLETED_DIR = "/root/speech2text/stream_onlineradio/transcribewave/recordings_processed_RJR"
POWER106_COMPLETED_DIR = "/root/speech2text/stream_onlineradio/transcribewave/recordings_processed_power106"

# Processing parameters
MAX_FILES_PER_RUN = 1  # Limit files per cron run to avoid timeouts


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
            # Skip .tmp files and .transcribing files
            if (file.suffix == '.tmp' or 
                file.name.endswith('.wav.tmp') or 
                file.name.endswith('.wav.transcribing')):
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
    # Remove .transcribing suffix if present
    if wav_name.endswith('.transcribing'):
        wav_name = wav_name[:-13]  # Remove '.transcribing'
    return os.path.join(transcripts_dir, f"{wav_name}_transcript.txt")

def is_already_transcribed(wav_file, transcripts_dir):
    """Check if WAV file has already been transcribed"""
    transcript_path = get_transcript_path(wav_file, transcripts_dir)
    return os.path.exists(transcript_path)

def mark_as_transcribing(wav_file):
    """
    Rename file to mark it as being transcribed.
    Returns the new path with .transcribing suffix, or None if rename fails.
    """
    transcribing_path = wav_file + ".transcribing"
    try:
        os.rename(wav_file, transcribing_path)
        return transcribing_path
    except Exception as e:
        print(f"Warning: Could not mark file as transcribing: {e}")
        return None

def unmark_transcribing(transcribing_file):
    """
    Remove .transcribing suffix from filename.
    Returns the original filename without .transcribing.
    """
    if transcribing_file.endswith('.transcribing'):
        return transcribing_file[:-13]  # Remove '.transcribing'
    return transcribing_file

def transcribe_single_file(client, wav_file, transcript_path, completed_dir, log_file):
    """Transcribe a single WAV file and move to completed directory"""
    original_wav_name = Path(wav_file).name
    log_message(f"🎤 Transcribing: {original_wav_name}", log_file)

    # Extract date and time from filename
    datetime_prefix = extract_datetime_from_filename(original_wav_name)

    # Mark file as being transcribed
    transcribing_file = mark_as_transcribing(wav_file)
    if transcribing_file is None:
        log_message(f"   ⚠️  Could not mark file as transcribing, using original", log_file)
        transcribing_file = wav_file
    else:
        log_message(f"   🏷️  Marked as transcribing", log_file)

    try:
        # Call HF Space API
        text = client.predict(handle_file(transcribing_file))
        #text = client.predict(handle_file(transcribing_file),api_name="/transcribe")

        if not text:
            text = "[Silence or unclear audio]"

        # Save transcript with datetime prefix
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"{datetime_prefix} {text}\n")

        log_message(f"   ✅ Saved to: {Path(transcript_path).name}", log_file)

        # Move WAV file to completed directory with original name (no .transcribing)
        try:
            os.makedirs(completed_dir, exist_ok=True)
            destination = os.path.join(completed_dir, original_wav_name)
            shutil.move(transcribing_file, destination)
            log_message(f"   📦 Moved to: {completed_dir}/{original_wav_name}", log_file)
        except Exception as e:
            log_message(f"   ⚠️  Could not move file: {e}", log_file)
            # Try to restore original filename
            try:
                original_path = unmark_transcribing(transcribing_file)
                if transcribing_file != original_path and os.path.exists(transcribing_file):
                    os.rename(transcribing_file, original_path)
                    log_message(f"   ↩️  Restored original filename", log_file)
            except:
                pass

        return True

    except Exception as e:
        log_message(f"   ❌ Transcription failed: {e}", log_file)

        # Restore original filename on failure
        try:
            original_path = unmark_transcribing(transcribing_file)
            if transcribing_file != original_path and os.path.exists(transcribing_file):
                os.rename(transcribing_file, original_path)
                log_message(f"   ↩️  Restored original filename after failure", log_file)
        except Exception as restore_error:
            log_message(f"   ⚠️  Could not restore filename: {restore_error}", log_file)

        return False


def extract_datetime_from_filename(filename):
    """Extract datetime from filename in format YYYYMMDD_HHMMSS and return as 'YYYYMMDD HHMMSS'"""
    pattern = r'_(\d{8})_(\d{6})_'
    match = re.search(pattern, filename)

    if match:
        date_str = match.group(1)  # YYYYMMDD
        time_str = match.group(2)  # HHMMSS
        return f"{date_str} {time_str}"

    # Fallback if pattern not found
    return "UNKNOWN_DATETIME"

def process_directory(station_name, recordings_dir, transcripts_dir, completed_dir, client, log_file):
    """Process all untranscribed WAV files in a directory"""
    log_message("=" * 60, log_file)
    log_message(f"📻 Processing {station_name} via RJR1", log_file)
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
        
        if transcribe_single_file(client, wav_file, transcript_path, completed_dir, log_file):
            successful += 1
        else:
            failed += 1
    
    log_message("-" * 60, log_file)
    log_message(f"📊 {station_name} Results(RJR1): {successful} successful, {failed} failed", log_file)
    log_message("=" * 60, log_file)
    
    return successful, failed

def main():
    
    log_message("=" * 60, log_file)
    log_message("📻 Batch WAV Transcription Service", log_file)
    log_message(f"🤗 HF Space: {HF_SPACE_URL}", log_file)
    log_message("=" * 60, log_file)
    
    # Connect to HF Space
    log_message("🤗 Connecting to Hugging Face Space...", log_file)
    try:
        client = Client(HF_SPACE_URL)
        log_message("✅ Connected successfully", log_file)
    except Exception as e:
        log_message(f"❌ Failed to connect: {e}", log_file)
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
            client, 
            log_file
        )
        total_successful += successful
        total_failed += failed
    else:
        log_message(f"⚠️  Directory not found: {RJR_RECORDINGS_DIR}", log_file)
   
    '''
    # Process Power106 recordings
    if os.path.exists(POWER106_RECORDINGS_DIR):
        successful, failed = process_directory(
            "Power106", 
            POWER106_RECORDINGS_DIR, 
            POWER106_TRANSCRIPTS_DIR,
            POWER106_COMPLETED_DIR,
            client, 
            log_file
        )
        total_successful += successful
        total_failed += failed
    else:
        log_message(f"⚠️  Directory not found: {POWER106_RECORDINGS_DIR}", log_file)
    '''
    
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
