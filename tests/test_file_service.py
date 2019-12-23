import os
import pytest
import tempfile
from latex.services.file_service import FileService


@pytest.fixture(scope="function")
def simple_temp_paths():
    with tempfile.TemporaryDirectory() as temp_path:
        temp0 = os.path.join(temp_path, "temp0")
        temp1 = os.path.join(temp_path, "temp1")
        os.makedirs(temp0)
        os.makedirs(temp1)
        service = FileService(temp0)
        yield service, temp0, temp1, temp_path


def make_test_files(sub_folder):
    sub_file0 = os.path.join(sub_folder, "test0.txt")
    sub_file1 = os.path.join(sub_folder, "test1.txt")
    os.makedirs(sub_folder)
    with open(sub_file0, "w") as handle:
        handle.write("test data 0")
    with open(sub_file1, "w") as handle:
        handle.write("test data 1")

    return sub_file0, sub_file1


def test_contains_directory_does_not_contain_self(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    assert not service.contains(temp0)


def test_contains_directory_does_not_contain_other(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    assert not service.contains(temp1)


def test_contains_directory_does_not_contain_other_subfolder(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub_folder = os.path.join(temp1, "sub_folder")
    assert not service.contains(sub_folder)


def test_contains_directory_does_not_contain_parent(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    assert not service.contains(parent)


def test_contains_subdirectory_works(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub_folder = os.path.join(temp0, "sub_folder")
    assert service.contains(sub_folder)


def test_contains_file_in_subdirectory_works(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub_folder = os.path.join(temp0, "sub_folder")
    sub_file = os.path.join(temp0, "test.txt")
    assert service.contains(sub_file)


def test_contains_up_tokens_fail(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub_folder = os.path.join(temp0, "..", "sub_folder")
    assert not service.contains(sub_folder)


def test_makedirs_throws_exception_on_other(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub_folder = os.path.join(temp1, "sub_folder")
    with pytest.raises(ValueError):
        service.makedirs(sub_folder)


def test_makedirs_works_on_contained(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub_folder = os.path.join(temp0, "sub_folder")
    service.makedirs(sub_folder)
    assert os.path.isdir(sub_folder)


def test_rmtree_throws_exception_on_other(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub_folder = os.path.join(temp1, "sub_folder")
    make_test_files(sub_folder)

    with pytest.raises(ValueError):
        service.rmtree(sub_folder)


def test_rmtree_works_on_contained(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub_folder = os.path.join(temp0, "sub_folder")
    f0, f1 = make_test_files(sub_folder)

    service.rmtree(sub_folder)

    assert not os.path.exists(f0)
    assert not os.path.exists(f1)


def test_get_all_files_throws_exception_on_other(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub_folder = os.path.join(temp1, "sub_folder")
    make_test_files(sub_folder)

    with pytest.raises(ValueError):
        service.get_all_files(sub_folder)


def test_get_all_files_works_with_subpath(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub0 = os.path.join(temp0, "sub0")
    sub1 = os.path.join(sub0, "sub1")
    f0, f1 = make_test_files(sub1)

    all_files = service.get_all_files(sub0)

    check0 = os.path.relpath(f0, sub0)
    check1 = os.path.relpath(f1, sub0)
    assert check0 in all_files
    assert check1 in all_files
    assert len(all_files) == 2


def test_get_all_files_works(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub0 = os.path.join(temp0, "sub0")
    f0, f1 = make_test_files(sub0)

    all_files = service.get_all_files(sub0)

    check0 = os.path.basename(f0)
    check1 = os.path.basename(f1)
    assert check0 in all_files
    assert check1 in all_files
    assert len(all_files) == 2


def test_opens_fails_outside_contained(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths

    with pytest.raises(ValueError):
        with service.open(os.path.join(temp1, "test.txt"), "w") as handle:
            handle.write("test")


def test_opens_for_read_inside_contained(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub0 = os.path.join(temp0, "sub0")
    f0, f1 = make_test_files(sub0)

    with service.open(f0, "r") as handle:
        assert handle.read() == "test data 0"


def test_opens_for_write_inside_contained(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    f0 = os.path.join(temp0, "test.txt")

    with service.open(f0, "w") as handle:
        handle.write("test data 0")

    with open(f0, "r") as handle:
        assert handle.read() == "test data 0"


def test_opens_for_write_with_relpath(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    f0 = os.path.join(temp0, "test.txt")

    with service.open("test.txt", "w") as handle:
        handle.write("test data 0")

    with open(f0, "r") as handle:
        assert handle.read() == "test data 0"


def test_exists_fails_outside_contained(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    f0, f1 = make_test_files(os.path.join(temp1, "sub"))

    with pytest.raises(ValueError):
        service.exists(f0)


def test_exists_positive_with_file(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    f0, f1 = make_test_files(os.path.join(temp0, "sub"))

    assert service.exists(f0)
    assert service.exists(os.path.relpath(f0, temp0))


def test_exists_negative_with_file(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    f0, f1 = make_test_files(os.path.join(temp0, "sub"))

    assert not service.exists(f0 + ".not")
    assert not service.exists(os.path.relpath(f0 + ".not", temp0))


def test_exists_positive_with_folder(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub = os.path.join(temp0, "sub")
    f0, f1 = make_test_files(sub)

    assert service.exists(sub)
    assert service.exists(os.path.relpath(sub, temp0))


def test_exists_negative_with_folder(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    sub = os.path.join(temp0, "sub")
    f0, f1 = make_test_files(sub)

    assert not service.exists(sub + "not")
    assert not service.exists(os.path.relpath(sub + "not", temp0))


def test_create_from_fails_outside_contained(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths

    with pytest.raises(ValueError):
        service.create_from(temp1)


def test_create_from_subdirectory(simple_temp_paths):
    service, temp0, temp1, parent = simple_temp_paths
    service.makedirs("test")

    created = service.create_from("test")

    assert type(created) is FileService
    assert created.root_path == os.path.join(service.root_path, "test", "")


