import numpy as np
import pytest

import face_store


def samples(n, value):
    return np.full((n, 8), value, dtype=np.uint8)


def test_add_and_remove_samples(tmp_path):
    path = tmp_path / "dataset.npz"
    assert face_store.add_samples(path, "user-a", samples(3, 1)) == 3
    assert face_store.add_samples(path, "user-b", samples(2, 2)) == 5

    assert face_store.remove_samples(path, "user-a") == 3
    dataset = face_store.load_dataset(path)
    assert len(dataset) == 2
    assert set(dataset.labels) == {"user-b"}


def test_replace_overwrites_existing_samples(tmp_path):
    path = tmp_path / "dataset.npz"
    face_store.add_samples(path, "user-a", samples(3, 1))
    assert face_store.add_samples(path, "user-a", samples(2, 9), replace=True) == 2
    assert (face_store.load_dataset(path).faces == 9).all()


def test_missing_dataset_is_empty(tmp_path):
    assert len(face_store.load_dataset(tmp_path / "none.npz")) == 0
    assert face_store.remove_samples(tmp_path / "none.npz", "user-a") == 0


@pytest.mark.parametrize("bad_id", ["../etc", "a b", "", "x" * 65])
def test_invalid_face_id_rejected(tmp_path, bad_id):
    with pytest.raises(ValueError):
        face_store.add_samples(tmp_path / "d.npz", bad_id, samples(1, 1))


def test_dimension_mismatch_rejected(tmp_path):
    path = tmp_path / "dataset.npz"
    face_store.add_samples(path, "user-a", samples(1, 1))
    with pytest.raises(ValueError):
        face_store.add_samples(path, "user-b", np.zeros((1, 4), dtype=np.uint8))
