import {
  Table,
  Column,
  Model,
  DataType,
  PrimaryKey,
  Default,
  ForeignKey,
  BelongsTo,
  CreatedAt,
  UpdatedAt
} from 'sequelize-typescript';
import { Route } from './Route';
import { Student } from './Student';

@Table({
  tableName: 'route_stops',
  timestamps: true,
  indexes: [
    {
      fields: ['route_id', 'stop_order']
    },
    {
      fields: ['student_id']
    },
    {
      type: 'SPATIAL',
      fields: ['location']
    }
  ]
})
export class RouteStop extends Model {
  @PrimaryKey
  @Default(DataType.UUIDV4)
  @Column(DataType.UUID)
  id!: string;

  @ForeignKey(() => Route)
  @Column({
    type: DataType.UUID,
    allowNull: false
  })
  routeId!: string;

  @ForeignKey(() => Student)
  @Column({
    type: DataType.UUID,
    allowNull: false
  })
  studentId!: string;

  @Column({
    type: DataType.INTEGER,
    allowNull: false
  })
  stopOrder!: number;

  @Column({
    type: DataType.ENUM('pickup', 'dropoff'),
    allowNull: false
  })
  stopType!: string;

  @Column({
    type: DataType.TIME,
    allowNull: false
  })
  scheduledTime!: string;

  @Column({
    type: DataType.TIME,
    allowNull: true
  })
  estimatedTime!: string;

  @Column({
    type: DataType.TIME,
    allowNull: true
  })
  actualTime!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  address!: string;

  @Column({
    type: DataType.FLOAT,
    allowNull: false
  })
  lat!: number;

  @Column({
    type: DataType.FLOAT,
    allowNull: false
  })
  lng!: number;

  @Column({
    type: DataType.GEOMETRY('POINT', 4326),
    allowNull: false
  })
  location!: any;

  @Column({
    type: DataType.FLOAT,
    allowNull: true
  })
  distanceFromPrevious!: number;

  @Column({
    type: DataType.INTEGER,
    allowNull: true
  })
  timeFromPrevious!: number;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: false
  })
  isClusterStop!: boolean;

  @Column({
    type: DataType.ARRAY(DataType.UUID),
    defaultValue: []
  })
  clusteredStudentIds!: string[];

  @Column({
    type: DataType.TEXT,
    allowNull: true
  })
  notes!: string;

  @CreatedAt
  createdAt!: Date;

  @UpdatedAt
  updatedAt!: Date;

  // Associations
  @BelongsTo(() => Route)
  route!: Route;

  @BelongsTo(() => Student)
  student!: Student;

  // Hooks to set geometry from lat/lng
  static async beforeSave(instance: RouteStop) {
    if (instance.lat && instance.lng) {
      instance.location = {
        type: 'Point',
        coordinates: [instance.lng, instance.lat],
        crs: { type: 'name', properties: { name: 'EPSG:4326' } }
      };
    }
  }
}