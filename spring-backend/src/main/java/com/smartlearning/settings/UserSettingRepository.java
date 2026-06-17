package com.smartlearning.settings;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.UUID;

public interface UserSettingRepository extends JpaRepository<UserSetting, UUID> {
}
