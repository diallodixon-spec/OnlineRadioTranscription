Audio Capture

===== record_segments_1minute.py =====
This script captures audio from 7 online radio stations. Audio is saved in 1 minute chunks i.e. there is a file for every minute of audio. The script captures audio for 1 hour, and is executed every hour from 9 am to 9 pm, Monday - Friday. As such captured audio for all radio stations is 9 am - 9 pm, Mon - Fri

  

Audio Transcription

===== transcribe_<NameOfRadioStation>.py ======
Each radio station has its own separate scripts for transcription. 
OpenAI Whisper is used for transcription. 
HuggingFace spaces act as workers and are used host code for transcription. To manage cost, the free tier of HuggingFace Spaces is used (otherwise this personal project would be quite expensive). Due to CPU and memory limitations on HuggingFace spaces, each radio station has 2 scripts which use 2 HuggingFace spaces for transcription alternatively.



Transription Analysis

===== transcript_analysis.py =====
This script uses LLM to assess the quality of the transcrption based on flow of words based on the topic/ideas, and assign a numerical score. This can be used to identify potentially inaccurate transcriptions and the associated audio file, which can then be manually reviewed.

===== transcription_analysis2.py =====
This script uses LLMs to summaries audio content in 30 minute blocks, and also detect and convert interviews into news articles. 
This is still a work in progress. This is currently using a one-shot prompt with lama-3.3-70B-Instruct-Turbo model, which incurs a cost. The goal is to use free smaller language models with smaller context (10 minute blocks instead of 30 minute blocks) and multiple passes.
