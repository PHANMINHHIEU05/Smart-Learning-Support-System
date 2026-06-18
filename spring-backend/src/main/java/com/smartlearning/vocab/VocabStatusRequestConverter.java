package com.smartlearning.vocab;

import org.springframework.core.convert.converter.Converter;
import org.springframework.stereotype.Component;

@Component
public class VocabStatusRequestConverter implements Converter<String, VocabStatus> {

    @Override
    public VocabStatus convert(String source) {
        return VocabStatus.fromValue(source);
    }
}
