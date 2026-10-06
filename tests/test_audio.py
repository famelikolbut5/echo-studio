from fastapi.testclient import TestClient
from backend import app as service

client=TestClient(service.app)

def test_checklist_has_traceable_evidence_not_fake_score():
    result=service.evaluate([{'start':4,'text':'Здравствуйте. Отправлю предложение.'}])
    assert result['score']==67
    assert result['checks'][0]['start']==4
    assert result['checks'][1]['passed'] is False
    assert result['checks'][1]['start'] is None
    assert 'не оценка LLM' in result['method']

def test_bad_upload_releases_worker_and_removes_file(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'ROOT',tmp_path)
    assert client.post('/api/transcriptions',files={'file':('bad.wav',b'not audio','audio/wav')}).status_code==422
    assert not service.LOCK.locked()
    assert not list(tmp_path.iterdir())

def test_unknown_job_and_audio():
    assert client.get('/api/transcriptions/missing').status_code==404
    assert client.get('/api/audio/missing').status_code==404
