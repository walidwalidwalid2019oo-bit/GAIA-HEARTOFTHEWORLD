plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "world.gaia.heart"
    compileSdk = 35

    defaultConfig {
        applicationId = "world.gaia.heart"
        minSdk = 23
        targetSdk = 35
        versionCode = 11
        versionName = "11.0-demo"
    }

    sourceSets {
        getByName("main") {
            // Package the existing mobile-first website inside the APK.
            assets.srcDir("../../website")
        }
}

dependencies {
    implementation("androidx.webkit:webkit:1.12.1")
}
