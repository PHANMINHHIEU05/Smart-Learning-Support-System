package com.smartlearning.vocab.extension;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface VocabExtensionPairingCodeRepository extends JpaRepository<VocabExtensionPairingCode, UUID> {

    Optional<VocabExtensionPairingCode> findByCodeHash(String codeHash);

    boolean existsByCodeHash(String codeHash);
}
