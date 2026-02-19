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
import { Student } from './Student';

@Table({
  tableName: 'schools',
  timestamps: true,
  indexes: [
    {
      fields: ['district_id']
    },
    {
      type: 'SPATIAL',
      fields: ['location']
    }
  ]
})
export class School extends Model {
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

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  name!: string;

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
    type: DataType.TIME,
    allowNull: false
  })
  startTime!: string;

  @Column({
    type: DataType.TIME,
    allowNull: false
  })
  endTime!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  principalName!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  contactEmail!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  contactPhone!: string;

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

  @HasMany(() => Student)
  students!: Student[];

  // Hooks to set geometry from lat/lng
  static async beforeSave(instance: School) {
    if (instance.lat && instance.lng) {
      instance.location = {
        type: 'Point',
        coordinates: [instance.lng, instance.lat],
        crs: { type: 'name', properties: { name: 'EPSG:4326' } }
      };
    }
  }
}