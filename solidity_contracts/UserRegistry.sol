// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract UserRegistry {
    struct User {
        string username;
        bool exists;
    }

    mapping(address => User) public users;

    event UserRegistered(address userAddress, string username);

    function registerUser(string memory _username) public {
        require(!users[msg.sender].exists, "User already registered");
        users[msg.sender] = User(_username, true);
        emit UserRegistered(msg.sender, _username);
    }

    function userExists(address _address) public view returns (bool) {
        return users[_address].exists;
    }

    function getUser(address _address) public view returns (string memory) {
        require(users[_address].exists, "User does not exist");
        return users[_address].username;
    }
}
