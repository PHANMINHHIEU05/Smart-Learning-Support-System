package com.smartlearning.vocab;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class VocabStatusConverter implements AttributeConverter<VocabStatus, String> {

    @Override
    public String convertToDatabaseColumn(VocabStatus attribute) {
        return attribute == null ? null : attribute.getValue();
    }

    @Override
    public VocabStatus convertToEntityAttribute(String dbData) {
        return dbData == null ? null : VocabStatus.fromValue(dbData);
    }
}
