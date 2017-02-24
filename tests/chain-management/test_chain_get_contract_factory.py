import pytest

import os

from populus.utils.filesystem import (
    remove_file_if_exists,
)
from populus.utils.linking import (
    link_bytecode_by_name,
)
from populus.chain import (
    NoKnownAddress,
    BytecodeMismatchError,
)
from populus.migrations import (
    Migration,
    DeployContract,
)
from populus.migrations.migration import (
    get_migration_classes_for_execution,
)
from populus.migrations.writer import (
    write_migration
)
from populus import Project


@pytest.mark.slow
def test_get_contract_factory_with_no_dependencies(temp_chain):
    chain = temp_chain

    MATH = chain.project.compiled_contracts['Math']
    Math = chain.get_contract_factory('Math')

    assert Math.bytecode == MATH['bytecode']
    assert Math.bytecode_runtime == MATH['bytecode_runtime']


@pytest.mark.slow
def test_get_contract_factory_with_missing_dependency(temp_chain):
    chain = temp_chain

    with pytest.raises(NoKnownAddress):
        Multiply13 = chain.get_contract_factory('Multiply13')



@pytest.mark.slow
def test_get_contract_factory_with_declared_dependency(temp_chain):
    chain = temp_chain

    MULTIPLY_13 = chain.project.compiled_contracts['Multiply13']
    Multiply13 = chain.get_contract_factory(
        'Multiply13',
        link_dependencies={
            'Library13': '0xd3cda913deb6f67967b99d67acdfa1712c293601',
        },
    )

    expected_code = link_bytecode_by_name(
        MULTIPLY_13['bytecode'],
        Library13='0xd3cda913deb6f67967b99d67acdfa1712c293601',
    )
    expected_runtime = link_bytecode_by_name(
        MULTIPLY_13['bytecode_runtime'],
        Library13='0xd3cda913deb6f67967b99d67acdfa1712c293601',
    )

    assert Multiply13.bytecode == expected_code
    assert Multiply13.bytecode_runtime == expected_runtime


@pytest.mark.slow
def test_get_contract_factory_with_registrar_dependency(temp_chain,
                                                        library_13):
    chain = temp_chain
    registrar = chain.registrar

    register_txn_hash = registrar.transact().setAddress(
        'contract/Library13', library_13.address,
    )

    chain.wait.for_receipt(register_txn_hash)

    MULTIPLY_13 = chain.project.compiled_contracts['Multiply13']
    Multiply13 = chain.get_contract_factory('Multiply13')

    expected_code = link_bytecode_by_name(
        MULTIPLY_13['bytecode'],
        Library13=library_13.address,
    )
    expected_runtime = link_bytecode_by_name(
        MULTIPLY_13['bytecode_runtime'],
        Library13=library_13.address,
    )

    assert Multiply13.bytecode == expected_code
    assert Multiply13.bytecode_runtime == expected_runtime


@pytest.mark.slow
def test_with_bytecode_mismatch_in_registrar_dependency(temp_chain,
                                                        library_13):
    chain = temp_chain
    registrar = chain.registrar

    # this will not match the expected underlying bytecode for the Library13
    # contract so it will cause a failure.
    register_txn_hash = registrar.transact().setAddress(
        'contract/Library13', '0xd3cda913deb6f67967b99d67acdfa1712c293601'
    )

    chain.wait.for_receipt(register_txn_hash)

    with pytest.raises(BytecodeMismatchError):
        chain.get_contract_factory('Multiply13')


@pytest.mark.slow
def test_bytecode_comes_from_project_if_no_migrations(temp_chain):
    project = Project()
    assert not project.migrations
    chain = temp_chain

    MATH = project.compiled_contracts['Math']
    Math = chain.get_contract_factory('Math')

    assert Math.abi == MATH['abi']
    assert Math.bytecode == MATH['bytecode']
    assert Math.bytecode_runtime == MATH['bytecode_runtime']