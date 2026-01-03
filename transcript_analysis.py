import os
from together import Together

# ------------------------------
# CONFIG
# ------------------------------
TRANSCRIPT_DIR_RJR = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_RJR"
TRANSCRIPT_DIR_Power106 = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_power106"
TRANSCRIPT_DIR_Nationwide = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_nationwide"
TRANSCRIPT_DIR_Newstalk93FM = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_newstalk93fm"
TRANSCRIPT_DIR_RootsFM = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_rootsfm"
TRANSCRIPT_DIR_NCUFM = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_ncufm"
TRANSCRIPT_DIR_SUNCITY = "/root/speech2text/stream_onlineradio/transcribewave/transcripts_suncity"
RECORDINGS_DIR_RJR = "/root/speech2text/stream_onlineradio/transcribewave/recordings_processed_RJR"
RECORDINGS_DIR_Power106 = "/root/speech2text/stream_onlineradio/transcribewave/recordings_processed_power106"
RECORDINGS_DIR_Nationwide = "/root/speech2text/stream_onlineradio/transcribewave/recordings_processed_nationwide"
RECORDINGS_DIR_Newstalk93FM = "/root/speech2text/stream_onlineradio/transcribewave/recordings_processed_newstalk93fm"
RECORDINGS_DIR_RootsFM = "/root/speech2text/stream_onlineradio/transcribewave/recordings_processed_rootsfm"
RECORDINGS_DIR_NCUFM = "/root/speech2text/stream_onlineradio/transcribewave/recordings_processed_ncufm"
RECORDINGS_DIR_Suncity = "/root/speech2text/stream_onlineradio/transcribewave/recordings_processed_suncity"
OUTPUT_LOG_FILE = "/root/speech2text/stream_onlineradio/transcribewave/logs/transcript_analysis_log.txt"  # Output file

TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
together_client = Together(api_key=TOGETHER_API_KEY)

MODEL_NAME = "ServiceNow-AI/Apriel-1.6-15b-Thinker"
#MODEL_NAME = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
#MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

SYSTEM_PROMPT = """
You will be given a speech-to-text transcript of 1 minute of radio audio. Your task is to evaluate the transcription accuracy on a scale of 0–100. The evaluation should be on the natural flow of words, ideas and topics. Note however that the start and end of the transcript may happen in the middle of a sentence, so incomplete sentences at the start and end of the transcription should not reduce the accuracy score. Also note that as it is transcription, Punctuations may not be 100% correct.

Output ONLY the number (0–100). No explanations.
"""

# ------------------------------
# FUNCTION: Score transcript
# ------------------------------
def score_transcription(text, client):
    if not client:
        return 0

    prompt = SYSTEM_PROMPT + "\n\nTranscript:\n" + text

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        # Extract the model's message content
        content = None
        if resp.choices and hasattr(resp.choices[0], "message"):
            msg = resp.choices[0].message
            if hasattr(msg, "content"):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get("content")
        if not content:
            return 0

        text_out = content.strip()
        # Remove code fences if present
        if text_out.startswith("```"):
            parts = text_out.split("```")
            if len(parts) >= 3:
                text_out = parts[1].strip()

        # Extract numeric score
        try:
            score = float(''.join(filter(str.isdigit, text_out)))
        except ValueError:
            score = 0

        return score

    except Exception as e:
        print(f"Error scoring transcript: {e}")
        return 0

# ------------------------------
# MAIN LOOP: Process transcripts
# ------------------------------
def process_transcripts():
    with open(OUTPUT_LOG_FILE, "a", encoding="utf-8") as log_file:
        for filename in os.listdir(TRANSCRIPT_DIR_RJR):
            # Only process .txt files and exclude already analyzed files
            if not filename.endswith(".txt") or "_LLManalyzed.txt" in filename:
                continue

            transcript_path = os.path.join(TRANSCRIPT_DIR_RJR, filename)

            # Map _transcript.txt -> .wav
            recording_name = filename.replace("_transcript.txt", ".wav")
            recording_path = os.path.join(RECORDINGS_DIR_RJR, recording_name)

            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Score transcript
            score = score_transcription(content, together_client)

            # Decide action
            if score > 0:
                if os.path.exists(recording_path):
                    os.remove(recording_path)
                    action = f"Deleted  {recording_path}"
                else:
                    action = f"Recording not found: {recording_path}"
            else:
                action = f"Kept  {recording_path}"

            # Write output to log file
            log_file.write(f"Scoring {filename}|{score}|{action}\n")
            log_file.write("Transcript content:\n")
            log_file.write(f"{content}\n")
            log_file.write("-" * 80 + "\n")

            # Rename transcript file to *_LLManalyzed.txt
            new_name = filename.replace(".txt", "_LLManalyzed.txt")
            new_path = os.path.join(TRANSCRIPT_DIR_RJR, new_name)
            os.rename(transcript_path, new_path)

        for filename in os.listdir(TRANSCRIPT_DIR_Power106):
            # Only process .txt files and exclude already analyzed files
            if not filename.endswith(".txt") or "_LLManalyzed.txt" in filename:
                continue

            transcript_path = os.path.join(TRANSCRIPT_DIR_Power106, filename)

            # Map _transcript.txt -> .wav
            recording_name = filename.replace("_transcript.txt", ".wav")
            recording_path = os.path.join(RECORDINGS_DIR_Power106, recording_name)

            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Score transcript
            score = score_transcription(content, together_client)

            # Decide action
            if score > 0:
                if os.path.exists(recording_path):
                    os.remove(recording_path)
                    action = f"Deleted  {recording_path}"
                else:
                    action = f"Recording not found: {recording_path}"
            else:
                action = f"Kept  {recording_path}"

            # Write output to log file
            log_file.write(f"Scoring {filename}|{score}|{action}\n")
            log_file.write("Transcript content:\n")
            log_file.write(f"{content}\n")
            log_file.write("-" * 80 + "\n")

            # Rename transcript file to *_LLManalyzed.txt
            new_name = filename.replace(".txt", "_LLManalyzed.txt")
            new_path = os.path.join(TRANSCRIPT_DIR_Power106, new_name)
            os.rename(transcript_path, new_path)

        for filename in os.listdir(TRANSCRIPT_DIR_Nationwide):
            # Only process .txt files and exclude already analyzed files
            if not filename.endswith(".txt") or "_LLManalyzed.txt" in filename:
                continue

            transcript_path = os.path.join(TRANSCRIPT_DIR_Nationwide, filename)

            # Map _transcript.txt -> .wav
            recording_name = filename.replace("_transcript.txt", ".wav")
            recording_path = os.path.join(RECORDINGS_DIR_Nationwide, recording_name)

            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Score transcript
            score = score_transcription(content, together_client)

            # Decide action
            if score > 0:
                if os.path.exists(recording_path):
                    os.remove(recording_path)
                    action = f"Deleted  {recording_path}"
                else:
                    action = f"Recording not found: {recording_path}"
            else:
                action = f"Kept  {recording_path}"

            # Write output to log file
            log_file.write(f"Scoring {filename}|{score}|{action}\n")
            log_file.write("Transcript content:\n")
            log_file.write(f"{content}\n")
            log_file.write("-" * 80 + "\n")

            # Rename transcript file to *_LLManalyzed.txt
            new_name = filename.replace(".txt", "_LLManalyzed.txt")
            new_path = os.path.join(TRANSCRIPT_DIR_Nationwide, new_name)
            os.rename(transcript_path, new_path)

        for filename in os.listdir(TRANSCRIPT_DIR_Newstalk93FM):
            # Only process .txt files and exclude already analyzed files
            if not filename.endswith(".txt") or "_LLManalyzed.txt" in filename:
                continue

            transcript_path = os.path.join(TRANSCRIPT_DIR_Newstalk93FM, filename)

            # Map _transcript.txt -> .wav
            recording_name = filename.replace("_transcript.txt", ".wav")
            recording_path = os.path.join(RECORDINGS_DIR_Newstalk93FM, recording_name)

            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Score transcript
            score = score_transcription(content, together_client)

            # Decide action
            if score > 0:
                if os.path.exists(recording_path):
                    os.remove(recording_path)
                    action = f"Deleted  {recording_path}"
                else:
                    action = f"Recording not found: {recording_path}"
            else:
                action = f"Kept  {recording_path}"

            # Write output to log file
            log_file.write(f"Scoring {filename}|{score}|{action}\n")
            log_file.write("Transcript content:\n")
            log_file.write(f"{content}\n")
            log_file.write("-" * 80 + "\n")

            # Rename transcript file to *_LLManalyzed.txt
            new_name = filename.replace(".txt", "_LLManalyzed.txt")
            new_path = os.path.join(TRANSCRIPT_DIR_Newstalk93FM, new_name)
            os.rename(transcript_path, new_path)

        for filename in os.listdir(TRANSCRIPT_DIR_NCUFM):
            # Only process .txt files and exclude already analyzed files
            if not filename.endswith(".txt") or "_LLManalyzed.txt" in filename:
                continue

            transcript_path = os.path.join(TRANSCRIPT_DIR_NCUFM, filename)

            # Map _transcript.txt -> .wav
            recording_name = filename.replace("_transcript.txt", ".wav")
            recording_path = os.path.join(RECORDINGS_DIR_NCUFM, recording_name)

            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Score transcript
            score = score_transcription(content, together_client)

            # Decide action
            if score > 0:
                if os.path.exists(recording_path):
                    os.remove(recording_path)
                    action = f"Deleted  {recording_path}"
                else:
                    action = f"Recording not found: {recording_path}"
            else:
                action = f"Kept  {recording_path}"

            # Write output to log file
            log_file.write(f"Scoring {filename}|{score}|{action}\n")
            log_file.write("Transcript content:\n")
            log_file.write(f"{content}\n")
            log_file.write("-" * 80 + "\n")

            # Rename transcript file to *_LLManalyzed.txt
            new_name = filename.replace(".txt", "_LLManalyzed.txt")
            new_path = os.path.join(TRANSCRIPT_DIR_NCUFM, new_name)
            os.rename(transcript_path, new_path)

        for filename in os.listdir(TRANSCRIPT_DIR_RootsFM):
            # Only process .txt files and exclude already analyzed files
            if not filename.endswith(".txt") or "_LLManalyzed.txt" in filename:
                continue

            transcript_path = os.path.join(TRANSCRIPT_DIR_RootsFM, filename)

            # Map _transcript.txt -> .wav
            recording_name = filename.replace("_transcript.txt", ".wav")
            recording_path = os.path.join(RECORDINGS_DIR_RootsFM, recording_name)

            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Score transcript
            score = score_transcription(content, together_client)

            # Decide action
            if score > 0:
                if os.path.exists(recording_path):
                    os.remove(recording_path)
                    action = f"Deleted  {recording_path}"
                else:
                    action = f"Recording not found: {recording_path}"
            else:
                action = f"Kept  {recording_path}"

            # Write output to log file
            log_file.write(f"Scoring {filename}|{score}|{action}\n")
            log_file.write("Transcript content:\n")
            log_file.write(f"{content}\n")
            log_file.write("-" * 80 + "\n")

            # Rename transcript file to *_LLManalyzed.txt
            new_name = filename.replace(".txt", "_LLManalyzed.txt")
            new_path = os.path.join(TRANSCRIPT_DIR_RootsFM, new_name)
            os.rename(transcript_path, new_path)

        for filename in os.listdir(TRANSCRIPT_DIR_SUNCITY):
            # Only process .txt files and exclude already analyzed files
            if not filename.endswith(".txt") or "_LLManalyzed.txt" in filename:
                continue

            transcript_path = os.path.join(TRANSCRIPT_DIR_SUNCITY, filename)

            # Map _transcript.txt -> .wav
            recording_name = filename.replace("_transcript.txt", ".wav")
            recording_path = os.path.join(RECORDINGS_DIR_Suncity, recording_name)

            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Score transcript
            score = score_transcription(content, together_client)

            # Decide action
            if score > 0:
                if os.path.exists(recording_path):
                    os.remove(recording_path)
                    action = f"Deleted  {recording_path}"
                else:
                    action = f"Recording not found: {recording_path}"
            else:
                action = f"Kept  {recording_path}"

            # Write output to log file
            log_file.write(f"Scoring {filename}|{score}|{action}\n")
            log_file.write("Transcript content:\n")
            log_file.write(f"{content}\n")
            log_file.write("-" * 80 + "\n")

            # Rename transcript file to *_LLManalyzed.txt
            new_name = filename.replace(".txt", "_LLManalyzed.txt")
            new_path = os.path.join(TRANSCRIPT_DIR_SUNCITY, new_name)
            os.rename(transcript_path, new_path)

# ------------------------------
# RUN SCRIPT
# ------------------------------
if __name__ == "__main__":
    process_transcripts()

