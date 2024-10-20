// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FileVerification {
    mapping(string => address) private fileOwners;

    event FileStored(string indexed fileHash, address owner);

    function storeFileHash(string memory fileHash, address owner) public {
        require(bytes(fileHash).length > 0, "File hash cannot be empty");
        require(owner != address(0), "Owner address cannot be zero");

        fileOwners[fileHash] = owner;
        emit FileStored(fileHash, owner);
    }

    function getFileOwner(string memory fileHash) public view returns (address) {
        require(bytes(fileHash).length > 0, "File hash cannot be empty");
        return fileOwners[fileHash];
    }
}
