import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def organize_transcripts(base_path='.'):
    """
    Organize transcript files into date-specific directories.
    
    Args:
        base_path: The base directory to search for transcripts_ folders (default: current directory)
    """
    # Calculate yesterday's date in YYYYMMDD format
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y%m%d')
    
    # Convert to Path object for easier manipulation
    base_path = Path(base_path)
    
    # Find all directories starting with "transcripts_"
    transcript_dirs = [d for d in base_path.iterdir() 
                      if d.is_dir() and d.name.startswith('transcripts_')]

    summary_dirs = [s for s in base_path.iterdir()
                      if s.is_dir() and s.name.startswith('summaries_')]

    interview_dirs = [i for i in base_path.iterdir()
                      if i.is_dir() and i.name.startswith('interviews_')]
    
    if not transcript_dirs:
        print("No directories starting with 'transcripts_' found.")
        return
    
    print(f"Looking for files with date: {date_str}")
    print(f"Found {len(transcript_dirs)} transcript directories\n")
    
    # Process each transcript directory
    for trans_dir in transcript_dirs:
        print(f"Processing: {trans_dir.name}")
        
        # Create date directory if it doesn't exist
        date_dir = trans_dir / date_str
        date_dir.mkdir(exist_ok=True)
        print(f"  Created/verified directory: {date_dir}")
        
        # Find all .txt files with the date in the filename
        moved_count = 0
        for file in trans_dir.iterdir():
            if file.is_file() and file.suffix == '.txt' and date_str in file.name:
                # Move the file to the date directory
                dest = date_dir / file.name
                shutil.move(str(file), str(dest))
                print(f"  Moved: {file.name}")
                moved_count += 1
        
        if moved_count == 0:
            print(f"  No files with date {date_str} found")
        else:
            print(f"  Total files moved: {moved_count}")
        print()

    '''
    for summ_dir in summary_dirs:
        print(f"Processing: {summ_dir.name}")

        date_dir = summ_dir / date_str
        date_dir.mkdir(exist_ok=True)
        print(f"  Created/verified directory: {date_dir}")

        moved_count = 0
        for file in summ_dir.iterdir():
            dest = date_dir / file.name
            shutil.move(str(file), str(dest))
            print(f"  Moved: {file.name}")
            moved_count += 1

        if moved_count == 0:
            print(f"  No files with date {date_str} found")
        else:
            print(f"  Total files moved: {moved_count}")
        print()

    for interv_dir in interview_dirs:
        print(f"Processing: {interv_dir.name}")

        date_dir = interv_dir / date_str
        date_dir.mkdir(exist_ok=True)
        print(f"  Created/verified directory: {date_dir}")

        moved_count = 0
        for file in interv_dir.iterdir():
            dest = date_dir / file.name
            shutil.move(str(file), str(dest))
            print(f"  Moved: {file.name}")
            moved_count += 1

        if moved_count == 0:
            print(f"  No files with date {date_str} found")
        else:
            print(f"  Total files moved: {moved_count}")
        print()
    '''

if __name__ == "__main__":
    # Run the organizer in the current directory
    # You can change '.' to any path you want to search
    organize_transcripts('/root/speech2text/stream_onlineradio/transcribewave')
    print("Done!")
