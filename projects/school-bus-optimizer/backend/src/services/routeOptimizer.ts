import { Client } from '@googlemaps/google-maps-services-js';
import { Student } from '../models/Student';
import { School } from '../models/School';
import { Bus } from '../models/Bus';
import { Route } from '../models/Route';
import { RouteStop } from '../models/RouteStop';
import { logger } from '../utils/logger';
import { redisHelpers } from '../config/redis';
import { sequelize } from '../config/database';

interface OptimizationOptions {
  districtId: string;
  schoolIds?: string[];
  routeType: 'morning' | 'afternoon' | 'both';
  constraints?: {
    maxRouteTime?: number; // minutes
    maxWalkDistance?: number; // miles
    earliestPickupTime?: string; // HH:mm
    optimizeFor?: 'distance' | 'time' | 'balanced';
  };
}

interface Stop {
  id: string;
  studentId: string;
  lat: number;
  lng: number;
  address: string;
  schoolId: string;
  pickupTime?: string;
}

interface OptimizedRoute {
  busId: string;
  stops: Stop[];
  totalDistance: number;
  totalTime: number;
  polyline?: string;
}

export class RouteOptimizer {
  private googleMapsClient: Client;
  private readonly DEFAULT_MAX_ROUTE_TIME = 60; // minutes
  private readonly DEFAULT_MAX_WALK_DISTANCE = 0.5; // miles
  private readonly CLUSTER_RADIUS = 0.3; // miles

  constructor() {
    this.googleMapsClient = new Client({});
  }

  async optimizeRoutes(options: OptimizationOptions): Promise<OptimizedRoute[]> {
    logger.info('Starting route optimization', options);

    try {
      // Check cache first
      const cached = await redisHelpers.getOptimizedRoute(options.districtId);
      if (cached && process.env.NODE_ENV === 'production') {
        logger.info('Returning cached route optimization');
        return cached;
      }

      // Fetch necessary data
      const { students, schools, buses } = await this.fetchData(options);

      if (students.length === 0) {
        logger.warn('No students found for optimization');
        return [];
      }

      if (buses.length === 0) {
        throw new Error('No available buses found');
      }

      // Step 1: Cluster nearby students
      const clusters = await this.clusterStudents(students, options.constraints);
      logger.info(`Created ${clusters.length} student clusters`);

      // Step 2: Create initial routes based on school destinations
      const initialRoutes = this.createInitialRoutes(clusters, schools, buses);

      // Step 3: Optimize each route
      const optimizedRoutes = await Promise.all(
        initialRoutes.map(route => this.optimizeRoute(route, options.constraints))
      );

      // Step 4: Balance routes if needed
      const balancedRoutes = this.balanceRoutes(optimizedRoutes, buses);

      // Step 5: Calculate final metrics and save
      const finalRoutes = await this.finalizeroutes(balancedRoutes, options);

      // Cache the results
      await redisHelpers.setOptimizedRoute(options.districtId, finalRoutes);

      logger.info(`Route optimization completed. Created ${finalRoutes.length} routes`);
      return finalRoutes;

    } catch (error) {
      logger.error('Route optimization failed:', error);
      throw error;
    }
  }

  private async fetchData(options: OptimizationOptions) {
    const whereClause: any = { active: true };
    if (options.schoolIds && options.schoolIds.length > 0) {
      whereClause.schoolId = options.schoolIds;
    }

    const students = await Student.findAll({
      where: whereClause,
      include: [{ model: School, attributes: ['id', 'name', 'lat', 'lng', 'startTime'] }]
    });

    const schoolIds = [...new Set(students.map(s => s.schoolId))];
    const schools = await School.findAll({
      where: { id: schoolIds, active: true }
    });

    const buses = await Bus.findAll({
      where: { 
        districtId: options.districtId,
        status: 'active',
        active: true
      },
      order: [['capacity', 'DESC']]
    });

    return { students, schools, buses };
  }

  private async clusterStudents(students: Student[], constraints?: any): Promise<Stop[][]> {
    const clusters: Stop[][] = [];
    const maxWalkDistance = constraints?.maxWalkDistance || this.DEFAULT_MAX_WALK_DISTANCE;
    const processed = new Set<string>();

    for (const student of students) {
      if (processed.has(student.id)) continue;

      const cluster: Stop[] = [{
        id: student.id,
        studentId: student.id,
        lat: student.lat,
        lng: student.lng,
        address: student.address,
        schoolId: student.schoolId
      }];

      // Find nearby students within walking distance
      for (const other of students) {
        if (other.id === student.id || processed.has(other.id)) continue;
        
        const distance = this.haversineDistance(
          student.lat, student.lng,
          other.lat, other.lng
        );

        if (distance <= this.CLUSTER_RADIUS && other.schoolId === student.schoolId) {
          cluster.push({
            id: other.id,
            studentId: other.id,
            lat: other.lat,
            lng: other.lng,
            address: other.address,
            schoolId: other.schoolId
          });
          processed.add(other.id);
        }
      }

      processed.add(student.id);
      
      // Calculate cluster centroid
      if (cluster.length > 1) {
        const centroid = this.calculateCentroid(cluster);
        clusters.push([{
          id: `cluster-${clusters.length}`,
          studentId: cluster[0].studentId, // Primary student
          lat: centroid.lat,
          lng: centroid.lng,
          address: `Cluster stop for ${cluster.length} students`,
          schoolId: cluster[0].schoolId
        }]);
      } else {
        clusters.push(cluster);
      }
    }

    return clusters;
  }

  private createInitialRoutes(clusters: Stop[][], schools: School[], buses: Bus[]) {
    const routes: { busId: string; stops: Stop[]; schoolId: string }[] = [];
    const schoolGroups = new Map<string, Stop[]>();

    // Group clusters by school
    for (const cluster of clusters) {
      const schoolId = cluster[0].schoolId;
      if (!schoolGroups.has(schoolId)) {
        schoolGroups.set(schoolId, []);
      }
      schoolGroups.get(schoolId)!.push(...cluster);
    }

    // Assign buses to schools based on capacity needs
    let busIndex = 0;
    for (const [schoolId, stops] of schoolGroups) {
      let remainingStops = [...stops];
      
      while (remainingStops.length > 0 && busIndex < buses.length) {
        const bus = buses[busIndex];
        const routeStops = remainingStops.splice(0, bus.capacity);
        
        routes.push({
          busId: bus.id,
          stops: routeStops,
          schoolId
        });

        if (remainingStops.length > 0) {
          busIndex++;
        }
      }
      busIndex++;
    }

    return routes;
  }

  private async optimizeRoute(route: any, constraints?: any): Promise<OptimizedRoute> {
    const { busId, stops, schoolId } = route;
    
    if (stops.length <= 2) {
      // No optimization needed for 1-2 stops
      return {
        busId,
        stops,
        totalDistance: 0,
        totalTime: 0
      };
    }

    // Apply nearest neighbor algorithm with 2-opt improvement
    const optimizedStops = await this.nearestNeighborWithTwoOpt(stops);
    
    // Calculate total distance and time
    const metrics = await this.calculateRouteMetrics(optimizedStops);

    return {
      busId,
      stops: optimizedStops,
      totalDistance: metrics.totalDistance,
      totalTime: metrics.totalTime,
      polyline: metrics.polyline
    };
  }

  private async nearestNeighborWithTwoOpt(stops: Stop[]): Promise<Stop[]> {
    // Start with nearest neighbor solution
    const tour = [stops[0]];
    const unvisited = stops.slice(1);

    while (unvisited.length > 0) {
      const current = tour[tour.length - 1];
      let nearest = unvisited[0];
      let minDistance = this.haversineDistance(
        current.lat, current.lng,
        nearest.lat, nearest.lng
      );

      for (let i = 1; i < unvisited.length; i++) {
        const distance = this.haversineDistance(
          current.lat, current.lng,
          unvisited[i].lat, unvisited[i].lng
        );
        if (distance < minDistance) {
          minDistance = distance;
          nearest = unvisited[i];
        }
      }

      tour.push(nearest);
      unvisited.splice(unvisited.indexOf(nearest), 1);
    }

    // Apply 2-opt improvement
    let improved = true;
    while (improved) {
      improved = false;
      
      for (let i = 1; i < tour.length - 2; i++) {
        for (let j = i + 1; j < tour.length - 1; j++) {
          const currentDistance = 
            this.haversineDistance(tour[i-1].lat, tour[i-1].lng, tour[i].lat, tour[i].lng) +
            this.haversineDistance(tour[j].lat, tour[j].lng, tour[j+1].lat, tour[j+1].lng);
          
          const newDistance = 
            this.haversineDistance(tour[i-1].lat, tour[i-1].lng, tour[j].lat, tour[j].lng) +
            this.haversineDistance(tour[i].lat, tour[i].lng, tour[j+1].lat, tour[j+1].lng);
          
          if (newDistance < currentDistance) {
            // Reverse the segment between i and j
            const segment = tour.slice(i, j + 1).reverse();
            tour.splice(i, j - i + 1, ...segment);
            improved = true;
          }
        }
      }
    }

    return tour;
  }

  private balanceRoutes(routes: OptimizedRoute[], buses: Bus[]): OptimizedRoute[] {
    // Sort routes by number of stops
    routes.sort((a, b) => b.stops.length - a.stops.length);

    // Try to balance by moving stops between routes
    for (let i = 0; i < routes.length - 1; i++) {
      const route1 = routes[i];
      const route2 = routes[i + 1];
      
      const bus1 = buses.find(b => b.id === route1.busId)!;
      const bus2 = buses.find(b => b.id === route2.busId)!;

      // If route1 is significantly longer and route2 has capacity
      if (route1.stops.length > route2.stops.length + 5 && 
          route2.stops.length < bus2.capacity * 0.8) {
        // Move some stops from route1 to route2
        const stopsToMove = Math.min(
          Math.floor((route1.stops.length - route2.stops.length) / 2),
          bus2.capacity - route2.stops.length
        );
        
        if (stopsToMove > 0) {
          const movedStops = route1.stops.splice(-stopsToMove);
          route2.stops.push(...movedStops);
        }
      }
    }

    return routes;
  }

  private async finalizeroutes(routes: OptimizedRoute[], options: OptimizationOptions) {
    const transaction = await sequelize.transaction();

    try {
      const savedRoutes = [];

      for (const route of routes) {
        // Create route record
        const routeRecord = await Route.create({
          districtId: options.districtId,
          busId: route.busId,
          routeName: `Route ${savedRoutes.length + 1}`,
          routeType: options.routeType,
          totalDistance: route.totalDistance,
          totalTime: route.totalTime,
          totalStudents: route.stops.length,
          polyline: route.polyline,
          optimizedAt: new Date(),
          optimizationMethod: 'nearest-neighbor-2opt',
          active: true,
          activeDays: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        }, { transaction });

        // Create route stops
        for (let i = 0; i < route.stops.length; i++) {
          const stop = route.stops[i];
          await RouteStop.create({
            routeId: routeRecord.id,
            studentId: stop.studentId,
            stopOrder: i + 1,
            stopType: options.routeType === 'afternoon' ? 'dropoff' : 'pickup',
            scheduledTime: this.calculateStopTime(i, route.totalTime),
            address: stop.address,
            lat: stop.lat,
            lng: stop.lng
          }, { transaction });
        }

        savedRoutes.push({
          ...route,
          routeId: routeRecord.id
        });
      }

      await transaction.commit();
      return savedRoutes;

    } catch (error) {
      await transaction.rollback();
      throw error;
    }
  }

  private async calculateRouteMetrics(stops: Stop[]) {
    let totalDistance = 0;
    let totalTime = 0;

    for (let i = 0; i < stops.length - 1; i++) {
      const distance = this.haversineDistance(
        stops[i].lat, stops[i].lng,
        stops[i + 1].lat, stops[i + 1].lng
      );
      totalDistance += distance;
      // Assume average speed of 25 mph in residential areas
      totalTime += (distance / 25) * 60; // convert to minutes
      // Add 1 minute per stop for pickup/dropoff
      totalTime += 1;
    }

    return {
      totalDistance: Math.round(totalDistance * 10) / 10,
      totalTime: Math.round(totalTime),
      polyline: '' // Would use Google Maps Directions API in production
    };
  }

  private haversineDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const R = 3959; // Earth's radius in miles
    const dLat = this.toRad(lat2 - lat1);
    const dLng = this.toRad(lng2 - lng1);
    
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
              Math.sin(dLng / 2) * Math.sin(dLng / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  private toRad(degrees: number): number {
    return degrees * (Math.PI / 180);
  }

  private calculateCentroid(points: Stop[]): { lat: number; lng: number } {
    const sum = points.reduce((acc, point) => ({
      lat: acc.lat + point.lat,
      lng: acc.lng + point.lng
    }), { lat: 0, lng: 0 });

    return {
      lat: sum.lat / points.length,
      lng: sum.lng / points.length
    };
  }

  private calculateStopTime(stopIndex: number, totalTime: number): string {
    // Assuming 7:00 AM start time
    const startHour = 7;
    const startMinute = 0;
    
    const minutesPerStop = totalTime / (stopIndex + 1);
    const stopMinutes = startMinute + (stopIndex * minutesPerStop);
    
    const hours = startHour + Math.floor(stopMinutes / 60);
    const minutes = Math.floor(stopMinutes % 60);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
  }
}