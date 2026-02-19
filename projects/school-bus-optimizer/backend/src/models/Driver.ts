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

@Table({
  tableName: 'drivers',
  timestamps: true,
  indexes: [
    {
      fields: ['district_id']
    },
    {
      fields: ['license_number'],
      unique: true
    }
  ]
})
export class Driver extends Model {
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
  firstName!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  lastName!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false,
    unique: true
  })
  licenseNumber!: string;

  @Column({
    type: DataType.DATE,
    allowNull: false
  })
  licenseExpiryDate!: Date;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  email!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  phone!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  emergencyContact!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  emergencyPhone!: string;

  @Column({
    type: DataType.TEXT,
    allowNull: true
  })
  address!: string;

  @Column({
    type: DataType.DATE,
    allowNull: true
  })
  hireDate!: Date;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: false
  })
  hasCommercialLicense!: boolean;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: false
  })
  hasPassedBackgroundCheck!: boolean;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: false
  })
  hasPassedDrugTest!: boolean;

  @Column({
    type: DataType.DATE,
    allowNull: true
  })
  lastDrugTestDate!: Date;

  @Column({
    type: DataType.DATE,
    allowNull: true
  })
  lastTrainingDate!: Date;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  photoUrl!: string;

  @Column({
    type: DataType.FLOAT,
    defaultValue: 0
  })
  rating!: number;

  @Column({
    type: DataType.INTEGER,
    defaultValue: 0
  })
  totalTrips!: number;

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

  @HasMany(() => Bus)
  buses!: Bus[];

  // Virtual fields
  get fullName(): string {
    return `${this.firstName} ${this.lastName}`;
  }
}