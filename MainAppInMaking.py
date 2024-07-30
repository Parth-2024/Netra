import boto3
import cv2
import tempfile
import os
import io
from PIL import Image
import time
from datetime import datetime
import google.generativeai as genai
import pygame
from botocore.exceptions import ClientError
import speech_recognition as sr
s3_client=boto3.client("s3",region_name="ap-south-1")
rek_client=boto3.client("rekognition",region_name="ap-south-1")
db_client=boto3.client("dynamodb",region_name="ap-south-1")
polly_client = boto3.client('polly',
                                aws_access_key_id="AKIA6ODU6OW7VEIYKA5D",
                                aws_secret_access_key="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",
                                region_name='ap-south-1'
                                )


def com(command):
    cmLst=['shoot','take']
    for cm in cmLst:
        if cm in command:
            return True
    return False

def up(command):
    upLst=['upload','face','person']
    for upld in upLst:
        if upld in command:
            return True
    return False

def download_file_from_s3(bucket_name, object_key, download_path):#It extracts the video from s3 and downloads it in the system
    try:
        s3_client.download_file(bucket_name, object_key, download_path)
        print(f"File downloaded to {download_path}")
        return download_path
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None

def download_videos(bucket,obj):
    local_download_path = os.path.join(os.getcwd(), 'downloaded_video.mp4')
    download_path = download_file_from_s3(bucket, obj, local_download_path)
    print("Download path:", download_path)

def extract_frames(local_video_path,frames_output_dir):#as the name of the function suggest, it extracts the frames from the video and create a temporary directory to store the extracted frames
    cap = cv2.VideoCapture(local_video_path)
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        frame_path = os.path.join(frames_output_dir, f"frame_{frame_count}.jpg")
        cv2.imwrite(frame_path, frame)
    cap.release()

def index_faces(output_dir,person_id,collection_id):#This is the main function as it uses AWS rekognition to scan the face of the person present in each frame of the input video. After scanning, it extracts faceids and label them under a specific PersonId(which is the name given by the user) 
    facelst=[]
    for filenames in os.listdir(output_dir):
        if filenames.endswith("jpg"):
            frame_path=os.path.join(output_dir,filenames)
            image=Image.open(f"{frame_path}")
            stream=io.BytesIO()
            image.save(stream,format="JPEG")
            image_binary=stream.getvalue()
            
            try:
                response=rek_client.index_faces(
                   CollectionId=collection_id,
                   Image={'Bytes':image_binary},
                   ExternalImageId=person_id
                #    DetectionAttributes=['All']
                )
                for faceRecords in response["FaceRecords"]:
                    faceId=faceRecords['Face']['FaceId']
                    facelst.append(faceId)
            except ClientError as e:
                print(f"An error occurred: {e}")


def extract_and_analyze_frames(local_video_path, frame_skip=5):#faster more optimized code, consuming less processing time
    cap = cv2.VideoCapture(local_video_path)
    frame_count = 0
    facelst = []
    faceSet = set()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_skip == 0:
            # Convert frame to JPEG format
            is_success, buffer = cv2.imencode(".jpg", frame)
            image_binary = buffer.tobytes()

            try:
                response = rek_client.search_faces_by_image(
                    CollectionId="mon_collection",
                    Image={'Bytes': image_binary},
                    FaceMatchThreshold=95
                )
                
                best_match = None
                highest_confidence = 0
                for match in response['FaceMatches']:
                    if match['Similarity'] > highest_confidence:
                        highest_confidence = match['Similarity']
                        best_match = match
                
                if best_match:
                    items = best_match['Face']['ExternalImageId']
                    if items:
                        person = items
                        facelst.append(person)
                        faceSet = set(facelst)
                        print(faceSet)
                        
            except ClientError as e:
                if e.response['Error']['Code'] == 'InvalidParameterException':
                    print("No faces detected")
                else:
                    print(f"An error occurred: {e}")

        frame_count += 1
    
    cap.release()
    return faceSet

# Non optimized form of code
'''  
# def extract_frames(local_video_path,frames_output_dir,frame_skip=5):
#     cap=cv2.VideoCapture(local_video_path)
#     frame_count=0
#     while cap.isOpened():
#         ret,frame=cap.read()
#         if not ret:
#             break
#         if frame_count%frame_skip==0:
#             frame_path=os.path.join(frames_output_dir,f"frame_{frame_count}.jpg")
#             cv2.imwrite(frame_path,frame)
#         frame_count+=1
#     cap.release()

# def analyse_frames(output_dir):#this function analyzes each frame present in the temporary directory and identifies the person by comparing their faceID(facial features) with the stored faceIds and print their names, stored as ExternalImageID, if it matches with any of the stored ones.
#     facelst=[]
#     faceSet=set()
#     for filenames in os.listdir(output_dir):
#         if filenames.endswith("jpg"):
#             frame_path=os.path.join(output_dir,filenames)
#             image=Image.open(f"{frame_path}")
#             stream=io.BytesIO()
#             image.save(stream,format="JPEG")
#             image_binary=stream.getvalue()
            
#             try:
#                 response = rek_client.search_faces_by_image(CollectionId="startup_collection", Image={'Bytes': image_binary},FaceMatchThreshold=95)
#                 best_match=None
#                 highest_confidence=0
#                 for match in response['FaceMatches']:
#                     if match['Similarity']>highest_confidence:
#                         highest_confidence=match['Similarity']
#                         best_match=match
#                         print(best_match['Face']['ExternalImageId'])
#                 if best_match:    
#                         items = best_match['Face']['ExternalImageId']
#                         if items:
#                             # Assuming there's only one match (faceId should ideally be unique)
#                             person = items
#                             print(person)
#                             facelst.append(person)
#                             faceSet=set(facelst)
#                             print(faceSet)
#             except ClientError as e:
#                 if e.response['Error']['Code'] == 'InvalidParameterException':
#                     print(f"No faces detected")
#                 else:
#                     print(f"An error occurred: {e}")
#     return faceSet'''

def convert_text_to_speech(text):#It converts the text description that we get from gemini into audio
        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId='Joanna'
        )
        audio_stream = response['AudioStream'].read()
        current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_filename = f'output_{current_time}.mp3'
        with open(output_filename, 'wb') as file:
            file.write(audio_stream)
        return output_filename

def play_audio_file(file_path):
        # Initialize the mixer module
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

def gemini_description(local_path,lst):
        
    def upload_to_gemini(path, mime_type=None):#Function for uploading the video in gemini for further processing
      """Uploads the given file to Gemini.
    
      See https://ai.google.dev/gemini-api/docs/prompting_with_media
      """
      file = genai.upload_file(path, mime_type=mime_type)
      print(f"Uploaded file '{file.display_name}' as: {file.uri}")
      return file
    
    def wait_for_files_active(files):#It preprocesses the file before giving it to gemini
      """Waits for the given files to be active.
    
      Some files uploaded to the Gemini API need to be processed before they can be
      used as prompt inputs. The status can be seen by querying the file's "state"
      field.
      """
      print("Waiting for file processing...")
      for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
          print(".", end="", flush=True)
          time.sleep(10)
          file = genai.get_file(name)
        if file.state.name != "ACTIVE":
          raise Exception(f"File {file.name} failed to process")
      print("...all files ready")
      print()

    genai.configure(api_key="AIzaSyBdEV4LX7Wag-eAXGa54w8gOE6pvMlwJsI")#API key for gemini
    
    
    generation_config = {
      "temperature": 1,
      "top_p": 0.95,
      "top_k": 64,
      "max_output_tokens": 8192,
      "response_mime_type": "text/plain",
    }
    
    model = genai.GenerativeModel(
      model_name="gemini-1.5-flash",
      generation_config=generation_config,
    )
    
    # Make these files available on the local file system
    files = [
      upload_to_gemini(local_path, mime_type="video/mp4"),
    ]#Uploads the file to gemini
    
    wait_for_files_active(files)
    
    chat_session = model.start_chat(
      history=[
            {
                "role": "user",
                "parts": [
                    files[0],
                ],
            },
        ]
    )
    
    response = chat_session.send_message(f"Instruction: Give a detailed description of this video in the most human way possible.Important Condition: Create an immersive experience for a blind person through your desciption. Describe it in a way that makes the blind person feel that he/she is living in the described moment and use simple 8th standard english. Remember: Provide the response in ssml format which is compatible with polly.Additional Reminder: If this list {lst} contains a name than use that name in the video description as the name of the person present in the video")
    #Sending a prompt to gemini to make it describe the uploaded video according to our needs
    if(lst):
        response=chat_session.send_message(f"Instruction: Add the names of the people given in this list {lst} to the description you provided in the previous prompt without changing it much.")
    print(response.text)
    audio=convert_text_to_speech(response.text)
    play_audio_file(audio)#Plays the audio description

def listen_to_voice():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source,duration=0.5)
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            return ""
        
def video_capture():#recording the video
    video_path='point.mp4'
    fourcc=cv2.VideoWriter_fourcc(*'mp4v')
    out=cv2.VideoWriter(video_path,fourcc,25,(640,480))

    cap=cv2.VideoCapture(2)
    if not cap.isOpened():
        print("Can't open the camera")
        exit()
    print("Starting to record a 15 second video")
    start_time=time.time()
    end_time=start_time+15 #for making sure that the shooting ends in 15 secs
    while time.time()<=end_time:
        ret,frame=cap.read()

        if not ret:
            print("Can't capture the frame")
        
        cv2.imshow("Recording",frame)
        out.write(frame)
        if cv2.waitKey(1) & 0xFF==ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    return video_path

def main_func():
    video_path=video_capture()
    lst=extract_and_analyze_frames(video_path)
    print(lst)
    gemini_description(video_path,lst)#when you will download the video from s3 than you will have to change video_path with download_path
    current_time=datetime.now()
    fileName=current_time.strftime("%D_%M_%Y_%H_%M")
    save=input("Do you want to save this video(Y/N):")
    if save=='Y':
        s3_client.upload_file(video_path, "video-recordingsss", f"{fileName}.mp4")#bucket name has to be dynamic as each user will be allocated a bucket of their own
    os.remove(video_path)

def face_upload():
    video_path=video_capture()
    try:
        person_id=input("Enter your name:")#take this from the input given by the user through the frontend
        collection_id="mon_collection"# Create a new collection #CollectionId will be dynamic as each user will have a unique CollectionId
        frames_dir="/tmp/frames"
        os.makedirs(frames_dir,exist_ok=True)
        extract_frames(video_path,frames_dir)
        index_faces(frames_dir,person_id,collection_id)
    except Exception as e:
        print(e)
        print("Error processing the video. ")

    
'''
    # download_path=download_file_from_s3(bucket_name,obj_key,local_path)#downloads the video from s3
        
    # os.makedirs(frames_dir,exist_ok=True)#makes a temperary directory where the frames are getting stored
    # extract_frames(download_path,frames_dir)#extracts the frams and stores them in the temp directory
        
    # lst=analyse_frames(frames_dir)#analyzes the frames and tries to recognize faces in them'''
if __name__=="__main__":
    while True:
        command=listen_to_voice()
        print(command)
        command=command.lower()
        shoot=com(command)
        upload=up(command)
        if shoot:
            main_func()
        if upload:
            face_upload()