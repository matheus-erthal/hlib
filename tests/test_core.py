from hlib.core import package_name  # importe algo que exista no seu pacote

def test_package_name():
    assert package_name() == "Hipólita"