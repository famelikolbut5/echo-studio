"""Word timestamps from faster-whisper; transparent rule-based quality checklist."""
import os
import threading
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI,HTTPException,UploadFile,File
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from .web import serve_web

app=FastAPI(title='Echo Studio')
ROOT=Path(os.environ.get('DEMO_DATA',Path(__file__).resolve().parents[1]/'data'))
ROOT.mkdir(parents=True,exist_ok=True)
JOBS={}
LOCK=threading.Lock()
MODEL=None

class Utterance(BaseModel):
    start:float=Field(ge=0)
    end:float=Field(ge=0)
    text:str=Field(max_length=4000)
    speaker:str='Не определён'

class Checklist(BaseModel):
    transcript:list[Utterance]=Field(max_length=300)

def evaluate(segments):
    rules=[('Приветствие',['здравств','добрый','hello']),('Выявление потребности',['нужно','нужен','интересует','need']),('Следующий шаг',['отправ','свяж','позвон','send'])]
    result=[]
    for label,terms in rules:
        evidence=next((s for s in segments if any(t in s['text'].lower() for t in terms)),None)
        result.append({'label':label,'passed':bool(evidence),'start':evidence['start'] if evidence else None,'evidence':evidence['text'] if evidence else 'Не найдено по ключевым словам'})
    return {'method':'Правила по ключевым словам; не оценка LLM','checks':result,'score':round(sum(x['passed'] for x in result)/len(result)*100)}

def transcribe(job,path):
    global MODEL
    try:
        JOBS[job]['state']='loading_model'
        from faster_whisper import WhisperModel
        if MODEL is None:
            MODEL=WhisperModel(os.environ.get('WHISPER_MODEL','tiny'),device='cpu',compute_type='int8')
        JOBS[job]['state']='transcribing'
        segments,info=MODEL.transcribe(str(path),word_timestamps=True,beam_size=3,vad_filter=True)
        transcript=[]
        for s in segments:
            transcript.append({'start':round(s.start,2),'end':round(s.end,2),'text':s.text.strip(),
                               'speaker':'Не определён','words':[{'start':w.start,'end':w.end,'text':w.word} for w in (s.words or [])]})
        JOBS[job].update(state='completed',transcript=transcript,language=info.language,checklist=evaluate(transcript),model=os.environ.get('WHISPER_MODEL','tiny'))
    except Exception:
        JOBS[job].update(state='failed',error='Транскрибация не завершилась. Проверьте доступ к модели и формат аудио.')
    finally:LOCK.release()

@app.get('/api/demo')
def demo():
    # Authored transcript from our synthetic sample; it is not inferred by a model.
    transcript=[{'start':0,'end':4.6,'speaker':'Менеджер','text':'Здравствуйте! Чем могу помочь?'},
                {'start':4.6,'end':9.6,'speaker':'Клиент','text':'Нужен комплект мебели для небольшого офиса.'},
                {'start':9.6,'end':13.727,'speaker':'Менеджер','text':'Отправлю предложение и свяжусь с вами завтра.'}]
    return {'id':'sample','state':'completed','transcript':transcript,'checklist':evaluate(transcript),'mode':'Авторская расшифровка синтетического аудио; роли заданы вручную','audio':'/api/sample'}

@app.get('/api/sample')
def sample():
    file=Path(__file__).resolve().parents[1]/'assets/sample.wav'
    if not file.exists(): raise HTTPException(404,'Синтетический пример ещё не сгенерирован')
    return FileResponse(file,media_type='audio/wav')

@app.post('/api/transcriptions')
async def upload(file:UploadFile=File(...)):
    if not LOCK.acquire(blocking=False):raise HTTPException(429,'Транскрибация занята')
    job=uuid4().hex
    path=ROOT/(job+'.audio')
    try:
        size=0
        with path.open('wb') as stream:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>30*1024*1024:raise HTTPException(413,'Максимум 30 МБ')
                stream.write(chunk)
        import av
        with av.open(str(path)) as media:
            if not media.streams.audio or not media.duration or media.duration>300_000_000:
                raise HTTPException(422,'Нужно аудио длительностью до 5 минут')
    except Exception as error:
        LOCK.release();path.unlink(missing_ok=True)
        if isinstance(error,HTTPException):raise
        raise HTTPException(422,'Не удалось прочитать аудио')
    JOBS[job]={'id':job,'state':'queued','audio':f'/api/audio/{job}'}
    threading.Thread(target=transcribe,args=(job,path),daemon=True).start()
    return JOBS[job]

@app.get('/api/transcriptions/{job}')
def status(job:str):
    if job not in JOBS:raise HTTPException(404)
    return JOBS[job]

@app.get('/api/audio/{job}')
def audio(job:str):
    if job not in JOBS:raise HTTPException(404)
    return FileResponse(ROOT/(job+'.audio'))

@app.post('/api/checklist')
def checklist(request:Checklist):return evaluate([s.model_dump() for s in request.transcript])

@app.get('/api/health')
def health():return {'status':'ok','asr_model':os.environ.get('WHISPER_MODEL','tiny'),'roles':'manual'}
serve_web(app)
