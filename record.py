import os
import sys
import subprocess
import wave
import threading
import time
from pathlib import Path
from datetime import datetime

# Configuration
#RJR
#RADIO_URL = "https://stream-148.zeno.fm/ebqnzkvyv9duv"

#Power106
RADIO_URL = "https://stream.zeno.fm/kke12ee08wquv"

OUTPUT_DIR = "recordings"

# Audio parameters
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPWIDTH = 2  # 16-bit
BYTES_PER_SAMPLE = 2
BYTES_PER_SECOND = SAMPLE_RATE * BYTES_PER_SAMPLE * CHANNELS

# Recording parameters
SEGMENT_DURATION_MINUTES = 5  # Create new file every N minutes
SEGMENT_DURATION_SECONDS = SEGMENT_DURATION_MINUTES * 60

class RadioRecorder:
    """Records online radio stream to WAV files"""
    
    def __init__(self, radio_url, output_dir):
        self.radio_url = radio_url
        self.output_dir = output_dir
        self.proc = None
        self.is_recording = False
        self.lock = threading.Lock()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def start_ffmpeg(self):
        """Start FFmpeg process to capture radio stream"""
        ffmpeg_cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-i", self.radio_url,
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
            "pipe:1"
        ]
        return subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**7
        )
    
    def create_filename(self, segment_num=None):
        """Create output filename with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if segment_num is not None:
            filename = f"radio_recording_{timestamp}_seg{segment_num:03d}.wav"
        else:
            filename = f"radio_recording_{timestamp}.wav"
        return os.path.join(self.output_dir, filename)
    
    def write_wav_header(self, wf, num_frames=0):
        """Write WAV file header"""
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPWIDTH)
        wf.setframerate(SAMPLE_RATE)
        if num_frames > 0:
            wf.setnframes(num_frames)
    
    def record_continuous(self, duration_seconds=None):
        """Record continuously to a single WAV file"""
        print("📻 Starting continuous recording...")
        
        output_file = self.create_filename()
        print(f"📁 Recording to: {output_file}")
        
        if duration_seconds:
            print(f"⏱️  Duration: {duration_seconds} seconds")
            print(f"⏱️  Duration: {duration_seconds/60:.1f} minutes")
        else:
            print("⏱️  Duration: Until stopped (Ctrl+C)")
        
        print("-" * 60)
        
        # Start FFmpeg
        self.proc = self.start_ffmpeg()
        self.is_recording = True
        
        start_time = time.time()
        bytes_written = 0
        
        try:
            with wave.open(output_file, 'wb') as wf:
                self.write_wav_header(wf)
                
                print("🎙️  Recording... (Press Ctrl+C to stop)")
                
                while self.is_recording:
                    # Check duration limit
                    if duration_seconds:
                        elapsed = time.time() - start_time
                        if elapsed >= duration_seconds:
                            print("\n⏱️  Duration limit reached")
                            break
                    
                    # Read audio data
                    chunk = self.proc.stdout.read(32768)
                    
                    if not chunk:
                        print("\n⚠️  Stream ended unexpectedly")
                        break
                    
                    # Write to WAV file
                    wf.writeframes(chunk)
                    bytes_written += len(chunk)
                    
                    # Show progress every 5 seconds
                    elapsed = time.time() - start_time
                    if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                        duration_recorded = bytes_written / BYTES_PER_SECOND
                        print(f"⏺️  Recording: {duration_recorded:.1f}s / {duration_recorded/60:.1f}m", end='\r')
        
        except KeyboardInterrupt:
            print("\n⏹️  Recording stopped by user")
        except Exception as e:
            print(f"\n❌ Error during recording: {e}")
        finally:
            self.cleanup()
            duration_recorded = bytes_written / BYTES_PER_SECOND
            print(f"✅ Recording complete: {duration_recorded:.1f} seconds ({duration_recorded/60:.1f} minutes)")
            print(f"📁 Saved to: {output_file}")
            
            # Get file size
            if os.path.exists(output_file):
                file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f"💾 File size: {file_size_mb:.2f} MB")
    
    def record_segmented(self, total_duration_minutes=None):
        """Record to multiple WAV files (segments)"""
        print("📻 Starting segmented recording...")
        print(f"📂 Output directory: {self.output_dir}")
        print(f"⏱️  Segment duration: {SEGMENT_DURATION_MINUTES} minutes")
        
        if total_duration_minutes:
            print(f"⏱️  Total duration: {total_duration_minutes} minutes")
        else:
            print("⏱️  Total duration: Until stopped (Ctrl+C)")
        
        print("-" * 60)
        
        # Start FFmpeg
        self.proc = self.start_ffmpeg()
        self.is_recording = True
        
        segment_num = 0
        start_time = time.time()
        
        try:
            while self.is_recording:
                # Check total duration limit
                if total_duration_minutes:
                    elapsed_minutes = (time.time() - start_time) / 60
                    if elapsed_minutes >= total_duration_minutes:
                        print("\n⏱️  Total duration limit reached")
                        break
                
                # Create new segment file
                output_file = self.create_filename(segment_num)
                print(f"\n🎙️  Recording segment {segment_num + 1}: {Path(output_file).name}")
                
                segment_start = time.time()
                bytes_written = 0
                
                with wave.open(output_file, 'wb') as wf:
                    self.write_wav_header(wf)
                    
                    while self.is_recording:
                        # Check segment duration
                        segment_elapsed = time.time() - segment_start
                        if segment_elapsed >= SEGMENT_DURATION_SECONDS:
                            break
                        
                        # Read audio data
                        chunk = self.proc.stdout.read(32768)
                        
                        if not chunk:
                            print("\n⚠️  Stream ended unexpectedly")
                            self.is_recording = False
                            break
                        
                        # Write to WAV file
                        wf.writeframes(chunk)
                        bytes_written += len(chunk)
                        
                        # Show progress
                        duration_recorded = bytes_written / BYTES_PER_SECOND
                        remaining = SEGMENT_DURATION_SECONDS - segment_elapsed
                        print(f"   ⏺️  {duration_recorded:.0f}s / {SEGMENT_DURATION_SECONDS}s (remaining: {remaining:.0f}s)", end='\r')
                
                # Segment complete
                duration_recorded = bytes_written / BYTES_PER_SECOND
                file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f"\n   ✅ Segment saved: {duration_recorded:.1f}s, {file_size_mb:.2f} MB")
                
                segment_num += 1
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Recording stopped by user")
        except Exception as e:
            print(f"\n❌ Error during recording: {e}")
        finally:
            self.cleanup()
            total_elapsed = (time.time() - start_time) / 60
            print(f"\n{'='*60}")
            print(f"✅ Recording complete")
            print(f"📊 Total segments: {segment_num}")
            print(f"⏱️  Total time: {total_elapsed:.1f} minutes")
            print(f"📁 Files saved to: {self.output_dir}/")
    
    def cleanup(self):
        """Clean up FFmpeg process"""
        self.is_recording = False
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except:
                self.proc.kill()

def main():
    print("📻 Online Radio Recorder")
    print("=" * 60)
    print(f"🔗 Radio URL: {RADIO_URL}")
    print("-" * 60)
    
    # Check FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg not found. Install with: sudo apt install ffmpeg")
        return 1
    
    # Show menu
    print("\nRecording Options:")
    print("1. Continuous recording (single file)")
    print("2. Segmented recording (multiple files)")
    print("-" * 60)
    
    try:
        choice = input("Select option (1 or 2): ").strip()
        
        recorder = RadioRecorder(RADIO_URL, OUTPUT_DIR)
        
        if choice == "1":
            # Continuous recording
            duration_input = input("\nDuration in minutes (or press Enter for unlimited): ").strip()
            duration_seconds = None
            if duration_input:
                try:
                    duration_seconds = int(float(duration_input) * 60)
                except ValueError:
                    print("⚠️  Invalid duration, recording until stopped")
            
            print()
            recorder.record_continuous(duration_seconds)
        
        elif choice == "2":
            # Segmented recording
            duration_input = input(f"\nTotal duration in minutes (or press Enter for unlimited): ").strip()
            total_duration = None
            if duration_input:
                try:
                    total_duration = float(duration_input)
                except ValueError:
                    print("⚠️  Invalid duration, recording until stopped")
            
            print()
            recorder.record_segmented(total_duration)
        
        else:
            print("❌ Invalid option")
            return 1
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
