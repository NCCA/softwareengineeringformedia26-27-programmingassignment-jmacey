import audiosample
import pytest
from audiosample import AudioSample


def test_audiosample_version():
    assert audiosample.__version__ == "0.0.0"


@pytest.fixture
def audio_sample():
    return AudioSample()


def test_construct_audio_sample(audio_sample):
    assert audio_sample
    assert audio_sample.sample_rate == 44100
    # set the sample rate
    audio_sample.sample_rate = 22050
    assert audio_sample.audio is None
    with pytest.raises(NotImplementedError):
        audio_sample.audio = 0


# ValueError should be thrown for <= 0 values
# TypeError should be thrown for other types
@pytest.mark.parametrize("value,exc", ((0, ValueError), (-20, ValueError), (0.0, TypeError), ("test", TypeError)))
def test_sample_rate_error(audio_sample, value, exc):
    with pytest.raises(exc):
        audio_sample.sample_rate = value


def test_create_sine_tone(audio_sample):
    duration = 0.1
    audio_sample.sine_tone(note="A", octave=4, duration=duration, amplitude=1.0)
    assert audio_sample.audio is not None
    assert len(audio_sample.audio) == int(audio_sample.sample_rate * duration)
