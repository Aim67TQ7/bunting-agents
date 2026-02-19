import { sequelize, enablePostGIS } from '../config/database';
import { District, School, Student, Bus, Driver, User, Route, RouteStop, GPSTracking } from '../models';
import { logger } from './logger';
import bcrypt from 'bcryptjs';

interface SeedOptions {
  districts?: number;
  schoolsPerDistrict?: number;
  studentsPerSchool?: number;
  busesPerDistrict?: number;
  driversPerDistrict?: number;
}

const DEFAULT_OPTIONS: SeedOptions = {
  districts: 2,
  schoolsPerDistrict: 3,
  studentsPerSchool: 50,
  busesPerDistrict: 10,
  driversPerDistrict: 10
};

// Sample data generators
const districtNames = ['Riverside', 'Oakwood', 'Meadowbrook', 'Hillcrest', 'Lakeside'];
const schoolNames = ['Elementary', 'Middle', 'High', 'Academy', 'Institute'];
const firstNames = ['Emma', 'Liam', 'Olivia', 'Noah', 'Ava', 'Ethan', 'Sophia', 'Mason', 'Isabella', 'William'];
const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez'];
const streetNames = ['Main', 'Oak', 'Maple', 'Cedar', 'Pine', 'Elm', 'Washington', 'Park', 'Lake', 'Hill'];

function randomElement<T>(array: T[]): T {
  return array[Math.floor(Math.random() * array.length)];
}

function generateAddress(baseCoords: { lat: number; lng: number }) {
  // Generate random address within ~5 mile radius
  const offsetLat = (Math.random() - 0.5) * 0.1; // ~5 miles
  const offsetLng = (Math.random() - 0.5) * 0.1;
  
  return {
    address: `${Math.floor(Math.random() * 9999) + 1} ${randomElement(streetNames)} Street`,
    lat: baseCoords.lat + offsetLat,
    lng: baseCoords.lng + offsetLng
  };
}

export async function seedDatabase(options: SeedOptions = DEFAULT_OPTIONS) {
  try {
    logger.info('Starting database seeding...');

    // Enable PostGIS
    await enablePostGIS();

    // Clear existing data (in reverse order of dependencies)
    await sequelize.query('SET CONSTRAINTS ALL DEFERRED');
    await RouteStop.destroy({ where: {} });
    await Route.destroy({ where: {} });
    await GPSTracking.destroy({ where: {} });
    await Student.destroy({ where: {} });
    await Bus.destroy({ where: {} });
    await Driver.destroy({ where: {} });
    await School.destroy({ where: {} });
    await User.destroy({ where: {} });
    await District.destroy({ where: {} });
    await sequelize.query('SET CONSTRAINTS ALL IMMEDIATE');

    logger.info('Cleared existing data');

    // Create districts
    const districts = [];
    for (let i = 0; i < (options.districts || DEFAULT_OPTIONS.districts!); i++) {
      const district = await District.create({
        name: `${randomElement(districtNames)} School District`,
        address: `${Math.floor(Math.random() * 999) + 1} District Plaza`,
        contactEmail: `admin@district${i + 1}.edu`,
        contactPhone: `555-${String(Math.floor(Math.random() * 900) + 100)}-${String(Math.floor(Math.random() * 9000) + 1000)}`,
        subscriptionTier: i === 0 ? 'enterprise' : 'professional',
        settings: {
          maxRouteTime: 60,
          maxWalkDistance: 0.5,
          defaultPickupBuffer: 5,
          notificationSettings: {
            smsEnabled: true,
            emailEnabled: true,
            pushEnabled: true
          },
          routeOptimizationSettings: {
            algorithm: 'nearest-neighbor',
            optimizeFor: 'balanced'
          }
        }
      });
      districts.push(district);
      logger.info(`Created district: ${district.name}`);
    }

    // Create admin users for each district
    for (const district of districts) {
      const adminUser = await User.create({
        districtId: district.id,
        email: `admin@${district.name.toLowerCase().replace(/\s+/g, '')}.edu`,
        password: 'admin123', // Will be hashed by model hook
        firstName: 'Admin',
        lastName: 'User',
        role: 'district_admin',
        emailVerified: true
      });
      logger.info(`Created admin user: ${adminUser.email}`);
    }

    // Create schools, students, buses, and drivers for each district
    for (const district of districts) {
      // Base coordinates for district (example: different US cities)
      const baseCoords = {
        lat: 40.7128 + (Math.random() - 0.5) * 10,
        lng: -74.0060 + (Math.random() - 0.5) * 10
      };

      // Create schools
      const schools = [];
      for (let i = 0; i < (options.schoolsPerDistrict || DEFAULT_OPTIONS.schoolsPerDistrict!); i++) {
        const schoolCoords = generateAddress(baseCoords);
        const school = await School.create({
          districtId: district.id,
          name: `${randomElement(districtNames)} ${randomElement(schoolNames)}`,
          address: schoolCoords.address,
          lat: schoolCoords.lat,
          lng: schoolCoords.lng,
          startTime: i === 0 ? '07:30' : i === 1 ? '08:00' : '08:30',
          endTime: i === 0 ? '14:30' : i === 1 ? '15:00' : '15:30',
          principalName: `${randomElement(firstNames)} ${randomElement(lastNames)}`,
          contactEmail: `principal.school${i + 1}@${district.name.toLowerCase().replace(/\s+/g, '')}.edu`,
          contactPhone: `555-${String(Math.floor(Math.random() * 900) + 100)}-${String(Math.floor(Math.random() * 9000) + 1000)}`
        });
        schools.push(school);
        logger.info(`Created school: ${school.name}`);

        // Create students for each school
        for (let j = 0; j < (options.studentsPerSchool || DEFAULT_OPTIONS.studentsPerSchool!); j++) {
          const studentCoords = generateAddress(baseCoords);
          const student = await Student.create({
            schoolId: school.id,
            firstName: randomElement(firstNames),
            lastName: randomElement(lastNames),
            grade: String(Math.floor(Math.random() * 12) + 1),
            address: studentCoords.address,
            lat: studentCoords.lat,
            lng: studentCoords.lng,
            parentName: `${randomElement(firstNames)} ${randomElement(lastNames)}`,
            parentEmail: `parent${j + 1}@email.com`,
            parentPhone: `555-${String(Math.floor(Math.random() * 900) + 100)}-${String(Math.floor(Math.random() * 9000) + 1000)}`,
            hasSpecialNeeds: Math.random() < 0.1,
            specialNeedsInfo: Math.random() < 0.1 ? 'Wheelchair accessible' : null
          });

          // Create parent user for first 10 students
          if (j < 10) {
            await User.create({
              districtId: district.id,
              email: student.parentEmail!,
              password: 'parent123',
              firstName: student.parentName!.split(' ')[0],
              lastName: student.parentName!.split(' ')[1] || 'Parent',
              role: 'parent',
              emailVerified: true
            });
          }
        }
      }
      logger.info(`Created ${options.studentsPerSchool} students per school`);

      // Create drivers
      const drivers = [];
      for (let i = 0; i < (options.driversPerDistrict || DEFAULT_OPTIONS.driversPerDistrict!); i++) {
        const driver = await Driver.create({
          districtId: district.id,
          firstName: randomElement(firstNames),
          lastName: randomElement(lastNames),
          licenseNumber: `DL${String(Math.floor(Math.random() * 900000) + 100000)}`,
          licenseExpiryDate: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), // 1 year from now
          email: `driver${i + 1}@${district.name.toLowerCase().replace(/\s+/g, '')}.edu`,
          phone: `555-${String(Math.floor(Math.random() * 900) + 100)}-${String(Math.floor(Math.random() * 9000) + 1000)}`,
          emergencyContact: `${randomElement(firstNames)} ${randomElement(lastNames)}`,
          emergencyPhone: `555-${String(Math.floor(Math.random() * 900) + 100)}-${String(Math.floor(Math.random() * 9000) + 1000)}`,
          address: generateAddress(baseCoords).address,
          hireDate: new Date(Date.now() - Math.random() * 365 * 5 * 24 * 60 * 60 * 1000), // Random date within last 5 years
          hasCommercialLicense: true,
          hasPassedBackgroundCheck: true,
          hasPassedDrugTest: true,
          lastDrugTestDate: new Date(Date.now() - Math.random() * 180 * 24 * 60 * 60 * 1000), // Within last 6 months
          rating: 4 + Math.random(),
          totalTrips: Math.floor(Math.random() * 1000)
        });
        drivers.push(driver);

        // Create driver user
        await User.create({
          districtId: district.id,
          email: driver.email!,
          password: 'driver123',
          firstName: driver.firstName,
          lastName: driver.lastName,
          role: 'driver',
          emailVerified: true
        });
      }
      logger.info(`Created ${drivers.length} drivers`);

      // Create buses
      for (let i = 0; i < (options.busesPerDistrict || DEFAULT_OPTIONS.busesPerDistrict!); i++) {
        const bus = await Bus.create({
          districtId: district.id,
          driverId: i < drivers.length ? drivers[i].id : null,
          vehicleNumber: `BUS-${String(i + 1).padStart(3, '0')}`,
          capacity: 40 + Math.floor(Math.random() * 30), // 40-70 seats
          make: randomElement(['Blue Bird', 'Thomas', 'IC Bus', 'Freightliner']),
          model: randomElement(['Vision', 'C2', 'CE Series', 'All American']),
          year: 2018 + Math.floor(Math.random() * 6),
          licensePlate: `SCH${String(Math.floor(Math.random() * 9000) + 1000)}`,
          status: i === 0 ? 'maintenance' : 'active',
          lastMaintenanceDate: new Date(Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000),
          nextMaintenanceDate: new Date(Date.now() + Math.random() * 90 * 24 * 60 * 60 * 1000),
          mileage: Math.floor(Math.random() * 100000),
          hasWheelchairLift: Math.random() < 0.3,
          hasAirConditioning: true,
          features: ['GPS', 'Camera System', 'Two-Way Radio']
        });
      }
      logger.info(`Created ${options.busesPerDistrict} buses`);
    }

    // Create a super admin user
    await User.create({
      districtId: districts[0].id,
      email: 'admin@schoolbusoptimizer.com',
      password: 'superadmin123',
      firstName: 'Super',
      lastName: 'Admin',
      role: 'admin',
      emailVerified: true
    });

    logger.info('Database seeding completed successfully!');
    
    // Log some test credentials
    logger.info('\n=== Test Credentials ===');
    logger.info('Super Admin: admin@schoolbusoptimizer.com / superadmin123');
    logger.info('District Admin: admin@riversideschooldistrict.edu / admin123');
    logger.info('Driver: driver1@riversideschooldistrict.edu / driver123');
    logger.info('Parent: parent1@email.com / parent123');
    logger.info('========================\n');

  } catch (error) {
    logger.error('Error seeding database:', error);
    throw error;
  }
}

// Run seeding if this file is executed directly
if (require.main === module) {
  sequelize.authenticate()
    .then(() => sequelize.sync({ force: true }))
    .then(() => seedDatabase())
    .then(() => {
      logger.info('Seeding complete!');
      process.exit(0);
    })
    .catch((error) => {
      logger.error('Seeding failed:', error);
      process.exit(1);
    });
}