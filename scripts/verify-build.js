const { execSync } = require('child_process');
const fs = require('fs');

console.log('Verifying build process...');

try {
  // Clean previous builds
  console.log('Cleaning previous builds...');
  execSync('rm -rf dist', { stdio: 'inherit' });
  
  // Run build
  console.log('Running build...');
  execSync('npm run build', { stdio: 'inherit' });
  
  // Check if build output exists
  if (fs.existsSync('dist')) {
    console.log('✅ Build successful! dist directory generated.');
  } else {
    console.error('❌ Build failed! dist directory not found.');
    process.exit(1);
  }
  
  console.log('✅ Build verification completed successfully!');
} catch (error) {
  console.error('❌ Build verification failed:', error.message);
  process.exit(1);
}