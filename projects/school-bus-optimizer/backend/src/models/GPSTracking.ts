import {
  Table,
  Column,
  Model,
  DataType,
  PrimaryKey,
  Default,
  ForeignKey,
  BelongsTo,
  CreatedAt
} from 'sequelize-typescript';
import { Bus } from './Bus';

@Table({
  tableName: 'gps_tracking',
  timestamps: false,
  indexes: [
    {
      fields: ['bus_id', 'timestamp']
    },
    {
      fields: ['timestamp']
    },
    {
      type: 'SPATIAL',
      fields: ['location']
    }
  ]
})
export class GPSTracking extends Model {
  @PrimaryKey
  @Default(DataType.UUIDV4)
  @Column(DataType.UUID)
  id!: string;

  @ForeignKey(() => Bus)
  @Column({
    type: DataType.UUID,
    allowNull: false
  })
  busId!: string;

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
  speed!: number;

  @Column({
    type: DataType.FLOAT,
    allowNull: true
  })
  heading!: number;

  @Column({
    type: DataType.FLOAT,
    allowNull: true
  })
  altitude!: number;

  @Column({
    type: DataType.FLOAT,
    allowNull: true
  })
  accuracy!: number;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  engineStatus!: string;

  @Column({
    type: DataType.FLOAT,
    allowNull: true
  })
  fuelLevel!: number;

  @Column({
    type: DataType.INTEGER,
    allowNull: true
  })
  odometer!: number;

  @CreatedAt
  @Column({
    type: DataType.DATE,
    defaultValue: DataType.NOW,
    field: 'timestamp'
  })
  timestamp!: Date;

  // Associations
  @BelongsTo(() => Bus)
  bus!: Bus;

  // Hooks to set geometry from lat/lng
  static async beforeSave(instance: GPSTracking) {
    if (instance.lat && instance.lng) {
      instance.location = {
        type: 'Point',
        coordinates: [instance.lng, instance.lat],
        crs: { type: 'name', properties: { name: 'EPSG:4326' } }
      };
    }
  }
}