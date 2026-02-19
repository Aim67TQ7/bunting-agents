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
import { School } from './School';
import { RouteStop } from './RouteStop';

@Table({
  tableName: 'students',
  timestamps: true,
  indexes: [
    {
      fields: ['school_id']
    },
    {
      type: 'SPATIAL',
      fields: ['location']
    }
  ]
})
export class Student extends Model {
  @PrimaryKey
  @Default(DataType.UUIDV4)
  @Column(DataType.UUID)
  id!: string;

  @ForeignKey(() => School)
  @Column({
    type: DataType.UUID,
    allowNull: false
  })
  schoolId!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  firstName!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  lastName!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  grade!: string;

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
    type: DataType.STRING,
    allowNull: true
  })
  parentName!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  parentEmail!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  parentPhone!: string;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: false
  })
  hasSpecialNeeds!: boolean;

  @Column({
    type: DataType.TEXT,
    allowNull: true
  })
  specialNeedsInfo!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  photoUrl!: string;

  @Column({
    type: DataType.TIME,
    allowNull: true
  })
  preferredPickupTime!: string;

  @Column({
    type: DataType.TIME,
    allowNull: true
  })
  preferredDropoffTime!: string;

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
  @BelongsTo(() => School)
  school!: School;

  @HasMany(() => RouteStop)
  routeStops!: RouteStop[];

  // Virtual fields
  get fullName(): string {
    return `${this.firstName} ${this.lastName}`;
  }

  // Hooks to set geometry from lat/lng
  static async beforeSave(instance: Student) {
    if (instance.lat && instance.lng) {
      instance.location = {
        type: 'Point',
        coordinates: [instance.lng, instance.lat],
        crs: { type: 'name', properties: { name: 'EPSG:4326' } }
      };
    }
  }
}