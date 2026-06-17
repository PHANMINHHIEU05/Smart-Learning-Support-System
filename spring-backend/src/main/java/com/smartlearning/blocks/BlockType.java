package com.smartlearning.blocks;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum BlockType {
    FOCUS("focus"),
    BREAK("break"),
    LONG_BREAK("long_break");

    private final String value;

    BlockType(String value) {
        this.value = value;
    }

    @JsonValue
    public String getValue() {
        return value;
    }

    @JsonCreator
    public static BlockType fromValue(String value) {
        for (BlockType type : values()) {
            if (type.value.equals(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unsupported block_type: " + value);
    }
}
