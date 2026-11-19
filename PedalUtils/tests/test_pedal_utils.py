import pedalutils
import pytest
from pedalutils import PedalDataset


@pytest.fixture
def manifest():
    return "/Users/jmacey/teaching/SEM/SEMAssignment26-27Jon/output_data/OMG_Capture/manifest.json"


def test_version():
    assert pedalutils.__version__ == "0.0.1"


def test_build_pedal_dataset(manifest):
    dataset = PedalDataset(manifest, window_frames=100)
    assert dataset
    # assert len(dataset) == 21194460
    input, output, controls = dataset[0]
    # assert input
    # assert output
    # assert controls
    print(input, output, controls)


def test_inputs(manifest):
    with pytest.raises(ValueError):
        _ = PedalDataset(manifest, window_frames=-20, hop_frames=20, output_offset_frames=0)
