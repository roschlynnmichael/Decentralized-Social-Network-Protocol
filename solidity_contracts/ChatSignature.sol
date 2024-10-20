// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ChatSignature {
    mapping(string => bytes) private chatSignatures;

    event ChatSigned(string indexed chatId, bytes signature);

    function storeChatSignature(string memory chatId, string memory chatHash, bytes memory signature) public {
        require(bytes(chatId).length > 0, "Chat ID cannot be empty");
        require(bytes(chatHash).length > 0, "Chat hash cannot be empty");
        require(signature.length > 0, "Signature cannot be empty");

        chatSignatures[chatId] = signature;
        emit ChatSigned(chatId, signature);
    }

    function getChatSignature(string memory chatId) public view returns (bytes memory) {
        require(bytes(chatId).length > 0, "Chat ID cannot be empty");
        return chatSignatures[chatId];
    }
}
