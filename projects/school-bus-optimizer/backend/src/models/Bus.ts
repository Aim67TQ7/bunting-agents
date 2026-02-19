import {
  Table,
  Column,
  Model,
  DataType,
  PrimaryKey,
  Default,
  ForeignKey,
  BelongsTo,
  HasMany,
  HasOne,
  CreatedAt,
  UpdatedAt
} from 'sequelize-typescript';
import { District } from './District';
import { Driver } from './Driver';
import { Route } from './Route';
import { GPSTracking } from './GPSTracking';

@Table({
  tableName: 'buses',
  timestamps: true,
  indexes: [
    {
      fields: ['district_id']
    },
    {
      fields: ['vehicle_number'],
      unique: true
    }
  ]
})
export class Bus extends Model {
  @PrimaryKey
  @Default(DataType.UUIDV4)
  @Column(DataType.UUID)
  id!: string;

  @ForeignKey(() => District)
  @Column({
    type: DataType.UUID,
    allowNull: false
  })
  districtId!: string;

  @ForeignKey(() => Driver)
  @Column({
    type: DataType.UUID,
    allowNull: true
  })
  driverId!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false,
    unique: true
  })
  vehicleNumber!: string;

  @Column({
    type: DataType.INTEGER,
    allowNull: false
  })
  capacity!: number;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  make!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  model!: string;

  @Column({
    type: DataType.INTEGER,
    allowNull: true
  })
  year!: number;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  licensePlate!: string;

  @Column({
    type: DataType.ENUM('active', 'maintenance', 'out-of-service'),
    defaultValue: 'active'
  })
  status!: string;

  @Column({
    type: DataType.DATE,
    allowNull: true
  })
  lastMaintenanceDate!: Date;

  @Column({
    type: DataType.DATE,
    allowNull: true
  })
  nextMaintenanceDate!: Date;

  @Column({
    type: DataType.INTEGER,
    defaultValue: 0
  })
  mileage!: number;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: false
  })
  hasWheelchairLift!: boolean;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: false
  })
  hasAirConditioning!: boolean;

  @Column({
    type: DataType.JSON,
    allowNull: true
  })
  features!: string[];

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: true
  })
  active!: boolean;

  @CreatedAt
  createdAt!: Date;

  @UpdatedAt
  updatedAt!: Date;

  // Associations
  @BelongsTo(() => District)
  district!: District;

  @BelongsTo(() => Driver)
  driver!: Driver;

  @HasMany(() => Route)
  routes!: Route[];

  @HasMany(() => GPSTracking)
  gpsTrackings!: GPSTracking[];
}