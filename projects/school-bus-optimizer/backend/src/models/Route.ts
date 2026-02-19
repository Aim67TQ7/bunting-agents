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
  CreatedAt,
  UpdatedAt
} from 'sequelize-typescript';
import { District } from './District';
import { Bus } from './Bus';
import { RouteStop } from './RouteStop';

@Table({
  tableName: 'routes',
  timestamps: true,
  indexes: [
    {
      fields: ['district_id']
    },
    {
      fields: ['bus_id']
    }
  ]
})
export class Route extends Model {
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

  @ForeignKey(() => Bus)
  @Column({
    type: DataType.UUID,
    allowNull: true
  })
  busId!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  routeName!: string;

  @Column({
    type: DataType.ENUM('morning', 'afternoon', 'both'),
    allowNull: false
  })
  routeType!: string;

  @Column({
    type: DataType.FLOAT,
    allowNull: false,
    defaultValue: 0
  })
  totalDistance!: number;

  @Column({
    type: DataType.INTEGER,
    allowNull: false,
    defaultValue: 0
  })
  totalTime!: number;

  @Column({
    type: DataType.INTEGER,
    allowNull: false,
    defaultValue: 0
  })
  totalStudents!: number;

  @Column({
    type: DataType.TIME,
    allowNull: true
  })
  startTime!: string;

  @Column({
    type: DataType.TIME,
    allowNull: true
  })
  endTime!: string;

  @Column({
    type: DataType.JSON,
    allowNull: true
  })
  polyline!: any;

  @Column({
    type: DataType.JSON,
    allowNull: true
  })
  directions!: any;

  @Column({
    type: DataType.DATE,
    allowNull: true
  })
  optimizedAt!: Date;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  optimizationMethod!: string;

  @Column({
    type: DataType.FLOAT,
    allowNull: true
  })
  estimatedFuelCost!: number;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: true
  })
  active!: boolean;

  @Column({
    type: DataType.ARRAY(DataType.STRING),
    defaultValue: []
  })
  activeDays!: string[];

  @CreatedAt
  createdAt!: Date;

  @UpdatedAt
  updatedAt!: Date;

  // Associations
  @BelongsTo(() => District)
  district!: District;

  @BelongsTo(() => Bus)
  bus!: Bus;

  @HasMany(() => RouteStop)
  stops!: RouteStop[];
}