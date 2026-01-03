import os
import re
from datetime import datetime, time
from pathlib import Path
from together import Together

# Configuration
DIRECTORIES_TO_CHECK = [
    "RJR",
    "rootsfm",
    "suncity",
    "newstalk93fm",
    "ncufm",
    "power106",
    "nationwide"
]
SOURCE_DIRECTORY = "/path/to/source_directory"  # Where to get files for concatenation
OUTPUT_DIRECTORY = "/root/speech2text/stream_onlineradio/transcribewave/summaries_"  # Where to save summaries
TOGETHER_API_KEY = "47a4fdd6780ae5683282eda5863f2dee674ab6b1118e66c062011b836ea28fd0"  # Set your API key

# Initialize Anthropic client
#client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
client = Together(api_key=TOGETHER_API_KEY)

def extract_time_from_filename(filename):
    """Extract time from filename. Format: RJR_recording_YYYYMMDD_HHMMSS_segXXX.wav"""
    # Pattern to match: YYYYMMDD_HHMMSS
    pattern = r'_(\d{8})_(\d{6})_'
    
    match = re.search(pattern, filename)
    if match:
        date_str = match.group(1)  # YYYYMMDD
        time_str = match.group(2)  # HHMMSS
        
        hour = int(time_str[0:2])
        minute = int(time_str[2:4])
        second = int(time_str[4:6])
        
        if 0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60:
            return time(hour, minute, second)
    
    return None

def is_time_in_range(file_time, start_hour, start_min, end_hour, end_min):
    """Check if file time falls within the specified range"""
    if file_time is None:
        return False
    start = time(start_hour, start_min)
    end = time(end_hour, end_min)
    return start <= file_time < end

def get_files_in_time_range(directory, start_hour, start_min, end_hour, end_min):
    """Get all files in directory that fall within the time range"""
    files = []
    full_path = '/root/speech2text/stream_onlineradio/transcribewave/recordings_' + directory
    
    if not os.path.exists(full_path):
        return files
    
    for filename in os.listdir(full_path):
        filepath = os.path.join(full_path, filename)
        if os.path.isfile(filepath):
            file_time = extract_time_from_filename(filename)
            if is_time_in_range(file_time, start_hour, start_min, end_hour, end_min):
                files.append(filepath)
    
    return sorted(files)

def get_files_in_time_range2(directory, start_hour, start_min, end_hour, end_min):
    """Get all files in directory that fall within the time range"""
    files = []
    full_path = '/root/speech2text/stream_onlineradio/transcribewave/transcripts_' + directory 

    if not os.path.exists(full_path):
        return files

    for filename in os.listdir(full_path):
        filepath = os.path.join(full_path, filename)
        if os.path.isfile(filepath):
            file_time = extract_time_from_filename(filename)
            if is_time_in_range(file_time, start_hour, start_min, end_hour, end_min):
                files.append(filepath)

    return sorted(files)

def concatenate_files(filepaths):
    """Read and concatenate content from multiple files"""
    content = []
    for filepath in filepaths:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content.append(f"--- Content from {os.path.basename(filepath)} ---\n")
                content.append(f.read())
                content.append("\n\n")
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    return "".join(content)

def summarize_with_llm(content):
    """Send content to LLM for summarization"""
    try:
        resp = client.chat.completions.create(
            #model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            model = "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": f"The provided texts are transcripts of a radio program. the transcriptions were done in 1 minute segments. the date and time for each segment appears at the start of the text of the transcription for each segment. e.g. \"2025-12-12 12:29:50 Everybody know! Yeah\" the date is 2025-12-12 and the time of this transcription is 12:29:50. the goal is to be able to determine date and time any particular topic was discussed. treat all segments as one body of text, and provide the topic or topics based on the transcription. if the host(s) are discussing a topic among themselves or by their self, include \"Host discussion\" in the topic. if there is an interview, include the word Interview in the topic. An interview is typically indicated by introduction of a guest(s) by the host and dialogue between host and guest(s) in a Q&A format. If callers are calling into the show, include \"Caller interaction\" in the topic. similar topics discussed in different time ranges with the same persons involved in the discussion can be merged into the same topic, with the multiple time ranges included. For each topic, provide the details of the topic and all NERs mentioned. include the time range for the topics. where appropriate, discussions on jamaica should be separate from other countries. prioritize accuracy and thoroughness over speed:\n\n{content}"
                }
            ],
            reasoning_effort="low"
        )
        #return message.content[0].text
        # Extract the model's message content
        content = None
        if resp.choices and hasattr(resp.choices[0], "message"):
            msg = resp.choices[0].message
            if hasattr(msg, "content"):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get("content")
            return content
    except Exception as e:
        print(f"Error calling API: {e}")
        return f"Error generating summary: {e}"

def save_summary(summary, output_dir, start_hour, start_min, end_hour, end_min):
    """Save summary to a file"""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"summary_{start_hour:02d}{start_min:02d}-{end_hour:02d}{end_min:02d}.txt"
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Summary for time range {start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d}\n")
            f.write("=" * 70 + "\n\n")
            f.write(summary)
        print(f"Summary saved to {filepath}")
    except Exception as e:
        print(f"Error saving summary: {e}")

def interviews_llm(content):
    """Send content to LLM to identify and extract interviews"""
    try:
        resp = client.chat.completions.create(
            model = "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            #model = "togethercomputer/Refuel-Llm-V2",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": f"The provided texts are transcripts of a radio program. The transcriptions were done in 1 minute segments. Your task is to identify ALL interviews in the transcript. An interview is typically indicated by introduction of a guest(s) by the host and dialogue between host and guest(s) in a Q&A format. Callers that call in to a radio program to discuss topics should not be identified as interviews, and should be excluded from this analysis. Multiple interviews found with the same host and guest should be treated as one single interview. For each interview found, rewrite as if it were a detailed news article. Ensure any line, sentence or quote with a high sentiment score is included i.e. anything inspiring, controversial, surprising, shocking, amusing, etc. If there are any quotes that are not logical, do not include those quotes. If NO interviews are found, respond with \"NO INTERVIEWS FOUND\". The only output should be the news article. Prioritize accuracy and thoroughness over speed:\n\n{content}"
                }
            ]
        )
        # Extract the model's message content
        content = None
        if resp.choices and hasattr(resp.choices[0], "message"):
            msg = resp.choices[0].message
            if hasattr(msg, "content"):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get("content")
            return content
    except Exception as e:
        print(f"Error calling API for interviews: {e}")
        return f"Error identifying interviews: {e}"

def save_interviews(interviews, output_dir, start_hour, start_min, end_hour, end_min):
    """Save interviews to a file"""
    # Check if no interviews were found
    if interviews and "NO INTERVIEWS FOUND" in interviews.upper():
        print(f"    No interviews found in this time range")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    filename = f"interviews_{start_hour:02d}{start_min:02d}-{end_hour:02d}{end_min:02d}.txt"
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Interviews for time range {start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d}\n")
            f.write("=" * 70 + "\n\n")
            f.write(interviews)
        print(f"    Interviews saved to {filepath}")
    except Exception as e:
        print(f"    Error saving interviews: {e}")

def process_directories():
    """Main processing function"""
    # Generate 30-minute time segments for the entire day
    time_segments = []
    for hour in range(9,21):
        time_segments.append((hour, 0, hour, 29))
        time_segments.append((hour, 30, hour, 59))
    
    for directory in DIRECTORIES_TO_CHECK:
        print(f"\nProcessing directory: {directory}")
        
        for start_hour, start_min, end_hour, end_min in time_segments:
            # Check if files exist in the current directory for this time range
            files_in_dir = get_files_in_time_range(directory, start_hour, start_min, end_hour, end_min)
            
            if not files_in_dir:
                print(f"  No files found for {start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}, checking source directory...")
                
                # Get files from source directory
                processed_files = get_files_in_time_range2(directory, start_hour, start_min, end_hour, end_min)
                
                if processed_files:
                    print(f"    Found {len(processed_files)} files in source directory")
                    
                    # Concatenate files
                    concatenated_content = concatenate_files(processed_files)
                    
                    if concatenated_content.strip():
                        # Summarize with LLM
                        print(f"    Sending to LLM for summarization...")
                        summary = summarize_with_llm(concatenated_content)
                        
                        # Save summary
                        OUTPUT_DIR = OUTPUT_DIRECTORY + directory
                        save_summary(summary, OUTPUT_DIR, start_hour, start_min, end_hour, end_min)
                        
                        # Check for interviews
                        #print(f"    Checking for interviews...")
                        #interviews = interviews_llm(concatenated_content)
                        
                        # Save interviews if found
                        #INTERVIEWS_DIR = "/root/speech2text/stream_onlineradio/transcribewave/interviews_" + directory
                        #save_interviews(interviews, INTERVIEWS_DIR, start_hour, start_min, end_hour, end_min)
                    else:
                        print(f"    No content to summarize")
                else:
                    print(f"    No files in source directory either")
            else:
                print(f"  Files already exist for {start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}, skipping")


if __name__ == "__main__":
    print("Starting file processing and summarization...")
    process_directories()
    print("\nProcessing complete!")
