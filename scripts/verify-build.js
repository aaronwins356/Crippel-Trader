const { execSync } = require('child_process');
const fs = require('fs');

console.log('Verifying build process...');

try {
  // Clean previous builds
  console.log('Cleaning previous builds...');
  execSync('rm -rf .next', { stdio: 'inherit' });
  
  // Run lint
  console.log('Running lint...');
  execSync('npm run lint', { stdio: 'inherit' });
  
  // Run build
  console.log('Running build...');
  execSync('npm run build', { stdio: 'inherit' });
  
  // Check if build output exists
  if (fs.existsSync('.next')) {
    console.log('✅ Build successful! .next directory generated.');
  } else {
    console.error('❌ Build failed! .next directory not found.');
    process.exit(1);
  }
  
  // Check for deprecation warnings in package-lock.json
  console.log('Checking for deprecated packages...');
  const packageLock = JSON.parse(fs.readFileSync('package-lock.json', 'utf8'));
  
  let hasDeprecations = false;
  if (packageLock.dependencies) {
    for (const [name, dep] of Object.entries(packageLock.dependencies)) {
      if (dep.deprecated) {
        console.warn(`⚠️  Deprecated: ${name} - ${dep.deprecated}`);
        hasDeprecations = true;
      }
    }
  }
  
  if (!hasDeprecations) {
    console.log('✅ No deprecated packages found in lockfile.');
  }
  
  console.log('✅ Build verification completed successfully!');
} catch (error) {
  console.error('❌ Build verification failed:', error.message);
  process.exit(1);
}